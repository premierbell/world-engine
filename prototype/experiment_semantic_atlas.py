"""Experiment #15: Semantic Atlas — 8개 도메인(Backend/AI/Database/Cloud/Security/
Sports/Finance/Science, 96개, 경계 사례 15개 포함)에서 embedding 공간이 실제로
어떻게 뭉치는지 관찰한다.

Finding #002(Semantic Boundary Ambiguity)는 Backend-AI 두 도메인에서만 나온
발견이었다. 이 실험은 "정답을 맞히는 것"이 목적이 아니다 — 8개 라벨은 여전히
Canonical Taxonomy(회귀 기준)로만 쓰고, 결론은 Semantic Evaluation
층("OpenAI 임베딩에서는 이러한 군집 경향이 관찰되었다")으로만 서술한다.
사람의 개념 체계를 증명하는 실험이 아니라는 것을 항상 전제한다.
"""

import json
from collections import defaultdict
from itertools import combinations

import matplotlib.pyplot as plt
import numpy as np
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from sklearn.cluster import HDBSCAN
from sklearn.preprocessing import normalize

from embedding_provider import OpenAIEmbeddingProvider
from similarity import cosine_similarity

console = Console()

DATASET_PATH = "../golden_dataset/semantic_atlas/dataset.json"
HEATMAP_PATH = "../experiments/plots/semantic_atlas_island_heatmap.png"
MIN_CLUSTER_SIZE_SWEEP = list(range(3, 13))
MIN_SAMPLES_SWEEP = [1, 2, 3]


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_dataset(path: str) -> dict[str, dict]:
    with open(path) as f:
        return json.load(f)


def avg_similarity(vectors_a: list[list[float]], vectors_b: list[list[float]], same_group: bool) -> float:
    if same_group:
        pairs = list(combinations(range(len(vectors_a)), 2))
        sims = [cosine_similarity(vectors_a[i], vectors_a[j]) for i, j in pairs]
    else:
        sims = [cosine_similarity(a, b) for a in vectors_a for b in vectors_b]
    return sum(sims) / len(sims) if sims else float("nan")


def run_hdbscan(
    keys: list[str], vectors: dict[str, list[float]], min_cluster_size: int, min_samples: int
) -> tuple[dict[str, int], set[int]]:
    matrix = normalize(np.array([vectors[key] for key in keys]))
    labels = HDBSCAN(
        min_cluster_size=min_cluster_size, min_samples=min_samples, metric="euclidean", copy=True
    ).fit_predict(matrix)
    next_noise_id = (int(labels.max()) + 1) if len(labels) else 0
    predicted: dict[str, int] = {}
    noise_ids: set[int] = set()
    for key, label in zip(keys, labels):
        if label == -1:
            predicted[key] = next_noise_id
            noise_ids.add(next_noise_id)
            next_noise_id += 1
        else:
            predicted[key] = int(label)
    return predicted, noise_ids


def main() -> None:
    load_dotenv()
    config = load_config()
    provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])

    dataset = load_dataset(DATASET_PATH)
    items = list(dataset.items())
    vectors = {key: provider.embed(entry["text"]) for key, entry in items}

    islands = sorted({entry["island"] for _, entry in items})
    vectors_by_island: dict[str, list[list[float]]] = defaultdict(list)
    for key, entry in items:
        vectors_by_island[entry["island"]].append(vectors[key])

    # 1. Island x Island 평균 pairwise 유사도 매트릭스
    matrix = np.zeros((len(islands), len(islands)))
    for i, isl_a in enumerate(islands):
        for j, isl_b in enumerate(islands):
            if j < i:
                matrix[i][j] = matrix[j][i]
                continue
            matrix[i][j] = avg_similarity(vectors_by_island[isl_a], vectors_by_island[isl_b], same_group=(i == j))

    matrix_table = Table(title="Experiment #15: Island x Island Average Pairwise Similarity")
    matrix_table.add_column("Island")
    for isl in islands:
        matrix_table.add_column(isl)
    for i, isl_a in enumerate(islands):
        row = [isl_a]
        for j, isl_b in enumerate(islands):
            val = matrix[i][j]
            row.append(f"[bold]{val:.3f}[/bold]" if i == j else f"{val:.3f}")
        matrix_table.add_row(*row)
    console.print(matrix_table)

    # 2. 각 Island가 자기 자신 다음으로 가장 가까운 Island는 어디인가
    nearest_table = Table(title="Experiment #15: Island별 가장 가까운 이웃 (자기 자신 제외)")
    for col in ("Island", "내부 유사도", "가장 가까운 이웃", "교차 유사도"):
        nearest_table.add_column(col)
    for i, isl_a in enumerate(islands):
        others = [(islands[j], matrix[i][j]) for j in range(len(islands)) if j != i]
        nearest_isl, nearest_sim = max(others, key=lambda p: p[1])
        nearest_table.add_row(isl_a, f"{matrix[i][i]:.3f}", nearest_isl, f"{nearest_sim:.3f}")
    console.print(nearest_table)

    # 3. Heatmap 저장
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(matrix, cmap="viridis", vmin=matrix.min(), vmax=matrix.max())
    ax.set_xticks(range(len(islands)))
    ax.set_yticks(range(len(islands)))
    ax.set_xticklabels(islands, rotation=45, ha="right")
    ax.set_yticklabels(islands)
    for i in range(len(islands)):
        for j in range(len(islands)):
            ax.text(j, i, f"{matrix[i][j]:.2f}", ha="center", va="center", color="white", fontsize=8)
    ax.set_title("Semantic Atlas: Island x Island Average Cosine Similarity")
    fig.colorbar(im)
    fig.tight_layout()
    fig.savefig(HEATMAP_PATH, dpi=150)
    console.print(f"[bold]Heatmap saved to {HEATMAP_PATH}[/bold]\n")

    # 4. HDBSCAN으로 "자연스럽게 몇 개가 나오는가" 관찰 (정답 맞히기가 아니라 관찰)
    keys = [key for key, _ in items]
    sweep_table = Table(title="Experiment #15: HDBSCAN min_cluster_size x min_samples sweep (관찰용, F1 없음)")
    for col in ("min_cluster_size", "min_samples", "Clusters(noise 제외)", "Noise 개수"):
        sweep_table.add_column(col)

    best_config = None
    for mcs in MIN_CLUSTER_SIZE_SWEEP:
        for ms in MIN_SAMPLES_SWEEP:
            predicted, noise_ids = run_hdbscan(keys, vectors, mcs, ms)
            n_clusters = len(set(predicted.values()) - noise_ids)
            n_noise = sum(1 for v in predicted.values() if v in noise_ids)
            sweep_table.add_row(str(mcs), str(ms), str(n_clusters), str(n_noise))
            if best_config is None and n_clusters not in (0, len(keys)) and n_noise < len(keys) * 0.3:
                best_config = (mcs, ms)

    console.print(sweep_table)

    if best_config is None:
        best_config = (5, 2)
    best_mcs, best_ms = best_config
    console.print(f"[bold]관찰용 설정: min_cluster_size={best_mcs}, min_samples={best_ms}[/bold]\n")

    predicted, noise_ids = run_hdbscan(keys, vectors, best_mcs, best_ms)
    cluster_composition: dict[int, list[tuple[str, str, bool]]] = defaultdict(list)
    for key, entry in items:
        cluster_composition[predicted[key]].append((entry["island"], entry["topic"], entry.get("boundary", False)))

    comp_table = Table(title=f"Experiment #15: HDBSCAN Cluster 구성 (mcs={best_mcs}, ms={best_ms})")
    for col in ("Cluster", "구성 (Island: 개수)", "포함된 경계 사례 Topic"):
        comp_table.add_column(col)

    real_clusters = sorted(c for c in cluster_composition if c not in noise_ids)
    noise_clusters = sorted(c for c in cluster_composition if c in noise_ids)

    for cluster_id in real_clusters + noise_clusters:
        members = cluster_composition[cluster_id]
        island_counts: dict[str, int] = defaultdict(int)
        boundary_topics = set()
        for island, topic, is_boundary in members:
            island_counts[island] += 1
            if is_boundary:
                boundary_topics.add(f"{topic}({island})")
        label = f"#{cluster_id}(noise)" if cluster_id in noise_ids else f"#{cluster_id}"
        composition_str = ", ".join(f"{isl}:{n}" for isl, n in sorted(island_counts.items(), key=lambda p: -p[1]))
        comp_table.add_row(label, composition_str, ", ".join(sorted(boundary_topics)) or "-")

    console.print(comp_table)


if __name__ == "__main__":
    main()
