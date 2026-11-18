"""
[측정 도구] 섬 좌표를 차원 축소(PCA/t-SNE)로 매번 다시 계산했다면 지도가 얼마나 흔들렸을지,
그리고 지금 방식(최근접 이웃 배치 + 좌표 영구 저장)이 의미를 얼마나 보존하는지 잰다 (2026-11-18).

입력 (개인 데이터라 레포에 두지 않는다 - scratchpad에서만 쓰고 지움):
  current.json               {"islands":[{id,x,y,embedding}], "scraps":[{id,createdAt,islandId,embedding}]}
  placement_embeddings.json  {"<islandId>": embedding}  - 좌표를 배치하던 시점의 섬 벡터(첫 스크랩, 11/17 백업)

실행: .venv/bin/python experiment_map_layout_stability.py <current.json> <placement_embeddings.json>

측정
  E1 실제 사건: 섬 벡터가 첫 스크랩 → 멤버 평균으로 바뀜(PR #148). 지금 방식은 좌표 그대로(DB 확인).
     PCA였다면 기존 섬이 얼마나 움직였나
  E2 섬을 만든 순서대로 하나씩 추가하며 매번 PCA로 다시 배치 - 기존 섬 이동량
  E3 스크랩 81개를 만든 순서대로 추가하며 PCA/t-SNE로 다시 배치 - 표본이 큰 쪽에서 같은 현상 확인
     + t-SNE는 같은 데이터에서 seed만 바꿔도 얼마나 달라지나
  E4 의미 보존: 임베딩 거리와 지도 거리의 순위 상관(Spearman), 가장 가까운 섬 일치 수
     - 지금 좌표 vs PCA vs 무작위 배치 1,000회

이동량 정의
  두 배치를 중심 맞춤 + 크기 정규화(RMS 반경 = 1) + 최적 회전·뒤집기·확대(Procrustes)로 맞춘 뒤 남는 거리.
  즉 "그림 전체를 돌리거나 뒤집은 것"은 이동으로 치지 않는다(PCA에 가장 유리한 비교). 단위는 지도 반경 대비 %.

사전 고정한 판단 기준 (측정 전에 정함)
  - PCA로 다시 배치해도 기존 섬 최대 이동 < 반경의 10%이고 가장 가까운 섬이 바뀐 경우가 0이면
    → "좌표 불변 원칙은 과잉 설계였다"고 기록한다
  - 지금 좌표의 Spearman이 무작위 배치 95백분위보다 낮으면
    → "지금 지도는 의미를 거의 반영하지 못한다"고 기록한다
"""

import json
import sys

import numpy as np
from scipy.linalg import orthogonal_procrustes
from scipy.stats import spearmanr
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

MOVE_THRESHOLD = 0.10
RANDOM_LAYOUTS = 1000


def normalize(vectors):
    matrix = np.asarray(vectors, dtype=float)
    return matrix / np.linalg.norm(matrix, axis=1, keepdims=True)


def pca_layout(vectors):
    return PCA(n_components=2).fit_transform(vectors)


def tsne_layout(vectors, seed):
    n = len(vectors)
    return TSNE(n_components=2, perplexity=min(30.0, (n - 1) / 3), init="pca",
                random_state=seed).fit_transform(vectors)


def _standardize(layout):
    centered = layout - layout.mean(axis=0)
    radius = np.sqrt((centered ** 2).sum(axis=1).mean())
    return centered / radius


def displacement(before, after):
    """after를 before에 Procrustes로 최대한 맞춘 뒤 점마다 남는 거리 (before 반경 = 1)."""
    a = _standardize(before)
    b = _standardize(after)
    rotation, _ = orthogonal_procrustes(b, a)
    b = b @ rotation
    b *= np.trace(a.T @ b) / np.trace(b.T @ b)
    return np.linalg.norm(b - a, axis=1)


def nearest(layout_or_vectors, cosine=False):
    x = np.asarray(layout_or_vectors, dtype=float)
    if cosine:
        dist = 1 - x @ x.T
    else:
        dist = np.linalg.norm(x[:, None, :] - x[None, :, :], axis=2)
    np.fill_diagonal(dist, np.inf)
    return dist.argmin(axis=1)


def neighbor_changes(before, after):
    return int((nearest(before) != nearest(after)).sum())


def pairwise(values, cosine=False):
    x = np.asarray(values, dtype=float)
    idx = np.triu_indices(len(x), k=1)
    if cosine:
        return (1 - x @ x.T)[idx]
    return np.linalg.norm(x[:, None, :] - x[None, :, :], axis=2)[idx]


def fidelity(vectors, layout):
    rho = spearmanr(pairwise(vectors, cosine=True), pairwise(layout)).statistic
    agree = int((nearest(vectors, cosine=True) == nearest(layout)).sum())
    return rho, agree


def replay(vectors, layout_fn, start):
    """앞에서부터 하나씩 추가하며 매번 다시 배치 - 단계마다 기존 점의 이동량과 이웃 변화."""
    steps = []
    previous = layout_fn(vectors[:start - 1])
    for k in range(start, len(vectors) + 1):
        current = layout_fn(vectors[:k])
        shared = current[:k - 1]
        moves = displacement(previous, shared)
        steps.append((k, float(np.median(moves)), float(moves.max()), neighbor_changes(previous, shared)))
        previous = current
    return steps


def pct(value):
    return f"{value * 100:.1f}%"


def summarize_replay(label, steps):
    medians = [s[1] for s in steps]
    maxima = [s[2] for s in steps]
    changes = [s[3] for s in steps]
    over = sum(1 for m in maxima if m >= MOVE_THRESHOLD)
    print(f"  {label}: 단계 {len(steps)}개 | 단계별 중앙 이동 중앙값 {pct(np.median(medians))} | "
          f"최대 이동 중앙값 {pct(np.median(maxima))}, 최댓값 {pct(max(maxima))} | "
          f"최대 이동 ≥10% 단계 {over}/{len(steps)} | 가장 가까운 점이 바뀐 경우 단계당 평균 {np.mean(changes):.1f}")


def main(current_path, placement_path):
    data = json.load(open(current_path, encoding="utf-8"))
    placement = json.load(open(placement_path, encoding="utf-8"))
    islands = sorted(data["islands"], key=lambda i: i["id"])
    stored = np.array([[i["x"], i["y"]] for i in islands], dtype=float)
    now_vectors = normalize([i["embedding"] for i in islands])
    old_vectors = normalize([placement[str(i["id"])] for i in islands])
    scraps = data["scraps"]
    scrap_vectors = normalize([s["embedding"] for s in scraps])

    print(f"섬 {len(islands)}개, 스크랩 {len(scraps)}개(임베딩 있는 것)\n")

    print("E1 실제 사건 - 섬 벡터 변경(#148): 첫 스크랩 → 멤버 평균")
    old_cos = (old_vectors * now_vectors).sum(axis=1)
    print(f"  섬 벡터 변화: 이전·이후 cosine {old_cos.min():.2f} ~ {old_cos.max():.2f}")
    print("  지금 방식: 좌표 변화 0 (DB의 11/17 백업 좌표 = 현재 좌표, 10/10)")
    moves = displacement(pca_layout(old_vectors), pca_layout(now_vectors))
    changed = neighbor_changes(pca_layout(old_vectors), pca_layout(now_vectors))
    print(f"  PCA였다면: 섬 이동 중앙값 {pct(np.median(moves))}, 최대 {pct(moves.max())}, "
          f"반경 10% 이상 이동한 섬 {int((moves >= MOVE_THRESHOLD).sum())}/{len(moves)}, "
          f"지도상 가장 가까운 섬이 바뀐 섬 {changed}/{len(moves)}\n")

    print("E2 섬을 만든 순서대로 추가하며 PCA 재배치 (배치 시점 벡터)")
    summarize_replay("PCA", replay(old_vectors, pca_layout, start=4))
    print()

    print("E3 스크랩을 만든 순서대로 추가하며 재배치 (10번째부터)")
    summarize_replay("PCA  ", replay(scrap_vectors, pca_layout, start=11))
    summarize_replay("t-SNE", replay(scrap_vectors, lambda v: tsne_layout(v, seed=0), start=11))
    seeds = [tsne_layout(scrap_vectors, seed=s) for s in range(5)]
    seed_moves = [displacement(seeds[0], other) for other in seeds[1:]]
    print(f"  t-SNE 같은 데이터, seed만 변경(4쌍): 이동 중앙값 {pct(np.median([np.median(m) for m in seed_moves]))}, "
          f"최대 {pct(max(m.max() for m in seed_moves))}\n")

    print("E4 의미 보존 - 임베딩 거리와 지도 거리의 Spearman / 가장 가까운 섬 일치")
    rng = np.random.default_rng(0)
    for label, vectors in (("배치 시점 벡터", old_vectors), ("지금 벡터", now_vectors)):
        stored_rho, stored_agree = fidelity(vectors, stored)
        pca_rho, pca_agree = fidelity(vectors, pca_layout(vectors))
        random_rhos = [fidelity(vectors, rng.uniform(size=(len(vectors), 2)))[0] for _ in range(RANDOM_LAYOUTS)]
        print(f"  [{label}] 지금 좌표 ρ={stored_rho:.2f}, 일치 {stored_agree}/{len(vectors)} | "
              f"PCA ρ={pca_rho:.2f}, 일치 {pca_agree}/{len(vectors)} | "
              f"무작위 ρ 평균 {np.mean(random_rhos):.2f}, 95백분위 {np.percentile(random_rhos, 95):.2f}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
