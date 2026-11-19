"""
[측정 도구] V2 배치(PR #162)로 실제로 놓인 새 섬을 재측정한다 (2026-11-19, 재검토 조건 "새 섬 5개 이상" 충족).

입력 (개인 데이터 - scratchpad에서만 쓰고 지움): current.json {"islands":[{id,x,y,embedding}], "scraps":[...]}

순서 (재검토 기준에 적어 둔 대로)
  1단계 --noise-only : 측정이 얼마나 흔들리는지만 잰다. 결과(V2가 나은지)는 출력하지 않는다
                       → 이걸 보고 판단 기준을 정한다
  2단계 (옵션 없이)   : 정한 기준으로 실제 좌표를 평가한다

섬 구분: id ≤ 10 = 옛 방식(V0)으로 놓인 섬(좌표 그대로), id ≥ 14 = V2로 놓인 새 섬 (11~13은 사용자가 삭제)

평가 대상
  A 실제 좌표 - DB에 저장된 그대로
  B 옛 방식 가정 - 옛 섬은 실제 좌표 그대로 두고, 새 섬만 V0로 다시 놓아 본 시뮬레이션
  C V2 시뮬레이션 - 같은 시뮬레이터로 새 섬을 V2로 놓은 것 (A를 시뮬레이터가 얼마나 재현하는지 확인용)
  새 섬을 놓을 때의 벡터: 새 섬 = 그 섬의 가장 이른 스크랩, 이미 놓인 섬 = 그 시점까지 만들어진 멤버 평균
  한계: 확정 시각은 저장되지 않아 스크랩 생성 시각으로 대신함, 삭제된 섬 11~13은 재현 불가

흔들림: 섬을 무작위로 80%만 뽑아 Spearman을 다시 계산(1,000회). 의미 보존은 지금 섬 벡터 기준

실행: .venv/bin/python experiment_map_layout_recheck.py <current.json> [--noise-only]
"""

import json
import sys

import numpy as np

from experiment_map_layout_calibration import _search_spot, radius, start_angle, thresholds
from experiment_map_layout_stability import fidelity, normalize

OLD_MAX_ID = 10
SUBSAMPLE_RATIO = 0.8
SUBSAMPLES = 1000


def load(path):
    data = json.load(open(path, encoding="utf-8"))
    islands = sorted(data["islands"], key=lambda i: i["id"])
    scraps = sorted([s for s in data["scraps"] if s["islandId"] is not None],
                    key=lambda s: (s["createdAt"], s["id"]))
    return islands, scraps


def first_scrap(island_id, scraps):
    return next(s for s in scraps if s["islandId"] == island_id)


def vector_at(island, before, scraps):
    members = [s["embedding"] for s in scraps
               if s["islandId"] == island["id"] and (s["createdAt"], s["id"]) < before]
    if not members:
        members = [first_scrap(island["id"], scraps)["embedding"]]
    mean = np.mean(np.asarray(members, dtype=float), axis=0)
    return mean / np.linalg.norm(mean)


def replay_new_islands(islands, scraps, variant):
    """옛 섬은 저장 좌표 그대로, 새 섬(id>10)만 순서대로 variant로 다시 놓는다."""
    coords = {i["id"]: np.array([i["x"], i["y"]], dtype=float) for i in islands if i["id"] <= OLD_MAX_ID}
    reasons = []
    for island in [i for i in islands if i["id"] > OLD_MAX_ID]:
        head = first_scrap(island["id"], scraps)
        before = (head["createdAt"], head["id"])
        placed = [i for i in islands if i["id"] in coords]
        placed_vectors = np.array([vector_at(i, before, scraps) for i in placed])
        placed_coords = np.array([coords[i["id"]] for i in placed])
        new = np.asarray(head["embedding"], dtype=float)
        new /= np.linalg.norm(new)
        sims = placed_vectors @ new
        anchor = int(sims.argmax())
        high, low = thresholds(variant, placed_vectors)
        r = radius(float(sims[anchor]), high, low)
        raw_anchor = np.asarray(first_scrap(placed[anchor]["id"], scraps)["embedding"], dtype=np.float32)
        angle0 = start_angle(variant, anchor, sims, raw_anchor, placed_coords)
        coords[island["id"]] = _search_spot(placed_coords, anchor, r, angle0)
        reasons.append((island["id"], float(sims[anchor]), high, low, r))
    return np.array([coords[i["id"]] for i in islands]), reasons


def subsample_scores(vectors, layouts, rng):
    n = len(vectors)
    size = int(round(n * SUBSAMPLE_RATIO))
    scores = {name: [] for name in layouts}
    for _ in range(SUBSAMPLES):
        idx = rng.choice(n, size=size, replace=False)
        for name, layout in layouts.items():
            scores[name].append(fidelity(vectors[idx], layout[idx])[0])
    return {name: np.array(values) for name, values in scores.items()}


def main(path, noise_only):
    islands, scraps = load(path)
    vectors = normalize([i["embedding"] for i in islands])
    stored = np.array([[i["x"], i["y"]] for i in islands], dtype=float)
    v0, _ = replay_new_islands(islands, scraps, "V0")
    v2, reasons = replay_new_islands(islands, scraps, "V2")
    layouts = {"A 실제 좌표": stored, "B 옛 방식 가정": v0}
    rng = np.random.default_rng(0)
    samples = subsample_scores(vectors, layouts, rng)
    diff = samples["A 실제 좌표"] - samples["B 옛 방식 가정"]
    n_new = sum(1 for i in islands if i["id"] > OLD_MAX_ID)

    print(f"섬 {len(islands)}개 (옛 {len(islands) - n_new}, V2로 놓인 새 섬 {n_new}), 스크랩 {len(scraps)}개\n")
    print(f"1단계 흔들림 - 섬 {int(SUBSAMPLE_RATIO * 100)}%를 무작위로 {SUBSAMPLES}번 뽑아 다시 계산")
    for name, values in samples.items():
        print(f"  {name}: Spearman 표준편차 {values.std():.3f}")
    print(f"  (A - B) 차이: 표준편차 {diff.std():.3f}")
    if noise_only:
        print("\n(--noise-only: 결과는 출력하지 않음 - 이 흔들림을 보고 판단 기준을 먼저 정한다)")
        return

    print("\n2단계 결과")
    random_rhos = [fidelity(vectors, rng.uniform(size=(len(vectors), 2)))[0] for _ in range(1000)]
    print(f"  무작위 배치 Spearman 95백분위 {np.percentile(random_rhos, 95):.2f}")
    for name, layout in {**layouts, "C V2 시뮬레이션": v2}.items():
        rho, agree = fidelity(vectors, layout)
        print(f"  {name}: Spearman {rho:.2f} | 가장 가까운 섬 일치 {agree}/{len(islands)}")
    print(f"  (A - B) 차이: 전체 {fidelity(vectors, stored)[0] - fidelity(vectors, v0)[0]:+.2f}, "
          f"부분표본 5~95백분위 {np.percentile(diff, 5):+.2f} ~ {np.percentile(diff, 95):+.2f}")
    new_index = [k for k, i in enumerate(islands) if i["id"] > OLD_MAX_ID]
    match = sum(1 for k in new_index if np.linalg.norm(stored[k] - v2[k]) < 1e-3)
    print(f"  시뮬레이터 재현: 새 섬 {match}/{n_new}개가 실제 좌표와 일치")
    print("  새 섬 배치 근거 (id, anchor 유사도, HIGH, LOW, 반경):")
    for island_id, sim, high, low, r in reasons:
        print(f"    {island_id}: {sim:.2f} | {high:.2f} | {low:.2f} | {r:.0f}")


if __name__ == "__main__":
    main(sys.argv[1], "--noise-only" in sys.argv[2:])
