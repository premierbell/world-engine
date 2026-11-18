"""
[측정 도구] 섬 배치(NearestNeighborCoordinateStrategy)의 유사도 → 거리 보정안을 시뮬레이션으로 비교한다 (2026-11-18).

배경 (experiment_map_layout_stability.py 결과):
  지금 상수(HIGH 0.95 / LOW 0.75)는 실제 섬 유사도(0.13~0.42)보다 훨씬 높아서, 9번의 배치가 모두 최대 거리 450을
  썼다. "얼마나 비슷한가"가 버려져 지도 거리와 의미 거리의 순위 상관이 무작위 수준이었다.

비교하는 배치 방식 (모두 배치 시점에 한 번만 계산 - 기존 섬은 움직이지 않는다는 원칙은 그대로)
  V0 지금 방식: 고정 상수 HIGH 0.95 / LOW 0.75, 시작 각도는 anchor 임베딩 해시
  V1 상대 보정: HIGH/LOW를 "이미 놓인 섬들끼리 유사도"의 90/10 백분위로 (놓인 섬이 3개 미만이면 V0 상수)
  V2 V1 + 방향: 시작 각도를 anchor에서 "anchor 다음으로 비슷한 섬들(유사도 가중 평균 위치)" 쪽으로
      (anchor 말고 놓인 섬이 없으면 V0처럼 해시 각도)
  거리 범위(120~450), 충돌 회피(8방향, 60씩 확장)는 Java 코드와 동일

데이터
  D1 실제 섬 10개를 만든 순서대로, 배치 당시 벡터(첫 스크랩)로 - 표본이 작음
  D2 스크랩 81개를 만든 순서대로 각각 섬이라고 보고 - 주 판단 데이터
  D3 운영 조건 재현(사후 추가): 실제 섬 10개를 첫 스크랩 시간순으로. 이미 놓인 섬 벡터는 그 시점까지 들어온 멤버의
     평균(PR #148 이후 운영 방식), 새 섬 벡터는 첫 스크랩. 평가는 지금 섬 벡터 기준
     - D1·D2는 같은 종류 벡터끼리라, 운영(새 섬 = 스크랩 하나, 기존 섬 = 멤버 평균)의 유사도 분포 차이를 못 봄
  (Java 배치를 Python으로 다시 구현한 것이라 저장된 실제 좌표를 그대로 재현하지는 않는다. 같은 시뮬레이터 안에서
   V0/V1/V2를 비교하는 것)

사전 고정한 채택 기준 (실행 전에 정함)
  (a) D1·D2 모두 순위 상관(Spearman)이 무작위 배치 95백분위를 넘고
  (b) D2에서 V0보다 Spearman이 0.15 이상 높을 것
  V1이 만족하면 V1(더 단순), V1이 안 되고 V2가 되면 V2, 둘 다 안 되면 보정하지 않고 발견만 기록한다.
  (D3 추가 후, 실행 전에 덧붙인 규칙) D3에서도 V0보다 높고 무작위 95백분위를 넘어야 채택한다.

실행: .venv/bin/python experiment_map_layout_calibration.py <current.json> <placement_embeddings.json>
"""

import json
import math
import struct
import sys

import numpy as np

from experiment_map_layout_stability import fidelity, normalize

MIN_DISTANCE = 120
MAX_DISTANCE = 450
CURVE_K = 2
DIRECTION_COUNT = 8
RADIUS_STEP = 60
MAX_RADIUS_EXPANSIONS = 20
FIXED_HIGH, FIXED_LOW = 0.95, 0.75
RANDOM_LAYOUTS = 1000
# 충돌 판정 여유값 - 최소 반경(120)으로 놓으면 후보와 anchor 거리가 정확히 120이라, 반올림 오차로 같은 자리가
# 빈자리/막힘으로 갈렸다(Java·Python 대조에서 발견). Java NearestNeighborCoordinateStrategy와 같은 값
COLLISION_EPSILON = 1e-6


def java_float_array_hash(vector):
    """Java Arrays.hashCode(float[]) - V0의 시작 각도를 Java와 같은 방식으로 만든다."""
    h = 1
    for value in vector:
        bits = struct.unpack(">i", struct.pack(">f", float(value)))[0]
        h = (31 * h + bits) & 0xFFFFFFFF
    return h - (1 << 32) if h >= (1 << 31) else h


def radius(similarity, high, low):
    normalized = min(max((high - similarity) / (high - low), 0.0), 1.0)
    return MIN_DISTANCE + (MAX_DISTANCE - MIN_DISTANCE) * normalized ** CURVE_K


def thresholds(variant, placed_vectors):
    if variant == "V0" or len(placed_vectors) < 3:
        return FIXED_HIGH, FIXED_LOW
    sims = placed_vectors @ placed_vectors.T
    pairs = sims[np.triu_indices(len(placed_vectors), k=1)]
    high, low = np.percentile(pairs, 90), np.percentile(pairs, 10)
    return (high, low) if high > low else (FIXED_HIGH, FIXED_LOW)


def start_angle(variant, anchor_index, sims, raw_anchor, coords):
    others = [i for i in range(len(coords)) if i != anchor_index and sims[i] > 0]
    if variant != "V2" or not others:
        return math.radians(java_float_array_hash(raw_anchor) % 360)
    weights = np.array([sims[i] for i in others])
    target = (coords[others] * weights[:, None]).sum(axis=0) / weights.sum()
    dx, dy = target - coords[anchor_index]
    if math.hypot(dx, dy) < 1e-9:
        return math.radians(java_float_array_hash(raw_anchor) % 360)
    return math.atan2(dy, dx)


def place(raw_vectors, variant):
    unit = normalize(raw_vectors)
    coords = np.zeros((0, 2))
    for k in range(len(unit)):
        if k == 0:
            coords = np.array([[0.0, 0.0]])
            continue
        placed = unit[:k]
        sims = placed @ unit[k]
        anchor = int(sims.argmax())
        high, low = thresholds(variant, placed)
        r = radius(float(sims[anchor]), high, low)
        angle0 = start_angle(variant, anchor, sims, raw_vectors[anchor], coords)
        spot = None
        for _ in range(MAX_RADIUS_EXPANSIONS):
            for i in range(DIRECTION_COUNT):
                angle = angle0 + 2 * math.pi * i / DIRECTION_COUNT
                candidate = coords[anchor] + r * np.array([math.cos(angle), math.sin(angle)])
                if np.all(np.linalg.norm(coords - candidate, axis=1) >= MIN_DISTANCE - COLLISION_EPSILON):
                    spot = candidate
                    break
            if spot is not None:
                break
            r += RADIUS_STEP
        if spot is None:
            spot = coords[anchor] + np.array([r, 0.0])
        coords = np.vstack([coords, spot])
    return coords


def _search_spot(coords, anchor, r, angle0):
    for _ in range(MAX_RADIUS_EXPANSIONS):
        for i in range(DIRECTION_COUNT):
            angle = angle0 + 2 * math.pi * i / DIRECTION_COUNT
            candidate = coords[anchor] + r * np.array([math.cos(angle), math.sin(angle)])
            if np.all(np.linalg.norm(coords - candidate, axis=1) >= MIN_DISTANCE - COLLISION_EPSILON):
                return candidate
        r += RADIUS_STEP
    return coords[anchor] + np.array([r, 0.0])


def place_production_replay(data, variant):
    """D3: 섬을 첫 스크랩 시간순으로 놓되, 놓인 섬 벡터는 그 시점 멤버 평균, 새 섬은 첫 스크랩 벡터."""
    scraps = [s for s in data["scraps"] if s["islandId"] is not None]
    scraps.sort(key=lambda s: (s["createdAt"], s["id"]))
    first = {}
    for scrap in scraps:
        first.setdefault(scrap["islandId"], scrap)
    order = sorted(data["islands"], key=lambda i: (first[i["id"]]["createdAt"], first[i["id"]]["id"]))

    def member_mean(island_id, before):
        members = [s["embedding"] for s in scraps
                   if s["islandId"] == island_id and (s["createdAt"], s["id"]) < before]
        mean = np.mean(np.asarray(members, dtype=float), axis=0)
        return mean / np.linalg.norm(mean)

    coords = np.array([[0.0, 0.0]])
    for k in range(1, len(order)):
        head = first[order[k]["id"]]
        before = (head["createdAt"], head["id"])
        new = np.asarray(head["embedding"], dtype=float)
        new /= np.linalg.norm(new)
        placed = np.array([member_mean(i["id"], before) for i in order[:k]])
        sims = placed @ new
        anchor = int(sims.argmax())
        high, low = thresholds(variant, placed)
        r = radius(float(sims[anchor]), high, low)
        raw_anchor = np.asarray(first[order[anchor]["id"]]["embedding"], dtype=np.float32)
        angle0 = start_angle(variant, anchor, sims, raw_anchor, coords)
        coords = np.vstack([coords, _search_spot(coords, anchor, r, angle0)])
    final_vectors = normalize([i["embedding"] for i in order])
    return final_vectors, coords


def random_p95(unit, rng):
    return float(np.percentile([fidelity(unit, rng.uniform(size=(len(unit), 2)))[0]
                                for _ in range(RANDOM_LAYOUTS)], 95))


def evaluate(label, raw_vectors, rng):
    unit = normalize(raw_vectors)
    p95 = random_p95(unit, rng)
    print(f"{label} (점 {len(unit)}개, 무작위 배치 Spearman 95백분위 {p95:.2f})")
    results = {}
    for variant in ("V0", "V1", "V2"):
        coords = place(raw_vectors, variant)
        rho, agree = fidelity(unit, coords)
        spread = float(np.sqrt(((coords - coords.mean(axis=0)) ** 2).sum(axis=1).mean()))
        min_gap = float(min(np.linalg.norm(coords[i] - coords[j])
                            for i in range(len(coords)) for j in range(i + 1, len(coords))))
        results[variant] = rho
        print(f"  {variant}: Spearman {rho:.2f} | 가장 가까운 점 일치 {agree}/{len(unit)} | "
              f"지도 반경(RMS) {spread:.0f} | 최소 간격 {min_gap:.0f}")
    return results, p95


def main(current_path, placement_path):
    data = json.load(open(current_path, encoding="utf-8"))
    placement = json.load(open(placement_path, encoding="utf-8"))
    islands = sorted(data["islands"], key=lambda i: i["id"])
    d1 = np.asarray([placement[str(i["id"])] for i in islands], dtype=np.float32)
    d2 = np.asarray([s["embedding"] for s in data["scraps"]], dtype=np.float32)
    rng = np.random.default_rng(0)

    r1, p1 = evaluate("D1 실제 섬 10개 (배치 당시 벡터)", d1, rng)
    print()
    r2, p2 = evaluate("D2 스크랩 81개를 섬으로 가정", d2, rng)
    print()

    final_vectors, _ = place_production_replay(data, "V0")
    p3 = random_p95(final_vectors, rng)
    print(f"D3 운영 조건 재현 (섬 10개, 평가는 지금 섬 벡터 기준, 무작위 배치 Spearman 95백분위 {p3:.2f})")
    r3 = {}
    for variant in ("V0", "V1", "V2"):
        _, coords = place_production_replay(data, variant)
        rho, agree = fidelity(final_vectors, coords)
        r3[variant] = rho
        print(f"  {variant}: Spearman {rho:.2f} | 가장 가까운 섬 일치 {agree}/{len(final_vectors)}")
    print()

    print("사전 기준 판정")
    for variant in ("V1", "V2"):
        a = r1[variant] > p1 and r2[variant] > p2
        b = r2[variant] - r2["V0"] >= 0.15
        c = r3[variant] > r3["V0"] and r3[variant] > p3
        print(f"  {variant}: (a) 무작위 95백분위 초과 D1 {r1[variant]:.2f}>{p1:.2f}, D2 {r2[variant]:.2f}>{p2:.2f} → {a} | "
              f"(b) D2 V0 대비 {r2[variant] - r2['V0']:+.2f} → {b} | "
              f"(D3) V0 {r3['V0']:.2f}보다 높고 {p3:.2f} 초과 {r3[variant]:.2f} → {c} | "
              f"채택 조건 {'만족' if a and b and c else '불만족'}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
