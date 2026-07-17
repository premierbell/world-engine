"""Experiment #18: Rank Corpus Replication + Rank Family Comparison.

Experiment #17(Semantic Factor Probe)은 6개 후보 중 "순위(Rank)"만
Sports+Finance에 특이적으로 가까웠지만(Specificity Gap +0.031), probe
문장이 단 하나(N=1)라 재현성이 없었다 — Candidate Hypothesis, Needs
Replication으로만 기록됨(`docs/algorithm_limitations.md` Finding #002).

이 실험은 두 부분으로 재현성을 검증한다:
1. Rank Corpus(20개, 서로 다른 phrasing) — 평균/표준편차/95% CI로 Experiment
   #17의 신호가 우연이 아닌지 확인한다.
2. Rank Family(Score/League/Standings/Leaderboard/Top N/Rating/Ranking/
   Index, 각 5개) — "Rank" 개념군 중 어떤 하위 개념이 Sports+Finance를
   가장 강하게 설명하는지 비교한다.
"""

import json
import statistics
from collections import defaultdict

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from similarity import cosine_similarity

console = Console()

ATLAS_DATASET_PATH = "../golden_dataset/semantic_atlas/dataset.json"
RANK_FAMILY_DATASET_PATH = "../golden_dataset/rank_family/dataset.json"


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_dataset(path: str) -> dict[str, dict]:
    with open(path) as f:
        return json.load(f)


def centroid(vectors: list[list[float]]) -> list[float]:
    n = len(vectors)
    dim = len(vectors[0])
    return [sum(v[i] for v in vectors) / n for i in range(dim)]


def specificity_gap(probe_vector: list[float], island_centroids: dict[str, list[float]]) -> float:
    sim_sports = cosine_similarity(probe_vector, island_centroids["Sports"])
    sim_finance = cosine_similarity(probe_vector, island_centroids["Finance"])
    other_islands = [isl for isl in island_centroids if isl not in ("Sports", "Finance")]
    max_other = max(cosine_similarity(probe_vector, island_centroids[isl]) for isl in other_islands)
    return min(sim_sports, sim_finance) - max_other


def confidence_interval_95(values: list[float]) -> tuple[float, float]:
    mean = statistics.mean(values)
    if len(values) < 2:
        return mean, mean
    stdev = statistics.stdev(values)
    margin = 1.96 * stdev / (len(values) ** 0.5)  # 정규근사, n=20이라 t-분포와 큰 차이 없음
    return mean - margin, mean + margin


def main() -> None:
    load_dotenv()
    config = load_config()
    provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])

    # Island centroid는 Experiment #17과 동일하게 semantic_atlas에서 재계산
    atlas = load_dataset(ATLAS_DATASET_PATH)
    atlas_items = list(atlas.items())
    atlas_vectors = {key: provider.embed(entry["text"]) for key, entry in atlas_items}
    vectors_by_island: dict[str, list[list[float]]] = defaultdict(list)
    for key, entry in atlas_items:
        vectors_by_island[entry["island"]].append(atlas_vectors[key])
    island_centroids = {isl: centroid(vecs) for isl, vecs in vectors_by_island.items()}

    rank_family = load_dataset(RANK_FAMILY_DATASET_PATH)
    rank_family_items = list(rank_family.items())
    probe_vectors = {key: provider.embed(entry["text"]) for key, entry in rank_family_items}

    gaps_by_concept: dict[str, list[float]] = defaultdict(list)
    for key, entry in rank_family_items:
        gap = specificity_gap(probe_vectors[key], island_centroids)
        gaps_by_concept[entry["concept"]].append(gap)

    # Part 1: Rank Corpus 재현성 (mean/std/95% CI)
    rank_gaps = gaps_by_concept["Rank"]
    ci_low, ci_high = confidence_interval_95(rank_gaps)

    rank_table = Table(title="Experiment #18a: Rank Corpus Replication (N=20)")
    for col in ("Metric", "Value"):
        rank_table.add_column(col)
    rank_table.add_row("Mean Specificity Gap", f"{statistics.mean(rank_gaps):+.4f}")
    rank_table.add_row("Std Dev", f"{statistics.stdev(rank_gaps):.4f}")
    rank_table.add_row("Min / Max", f"{min(rank_gaps):+.4f} / {max(rank_gaps):+.4f}")
    rank_table.add_row("95% CI", f"[{ci_low:+.4f}, {ci_high:+.4f}]")
    rank_table.add_row("양수 비율 (20개 중)", f"{sum(1 for g in rank_gaps if g > 0)}/20")
    console.print(rank_table)
    console.print(
        "[bold]95% CI가 0을 포함하지 않으면 Experiment #17의 신호가 우연이 아니라는 "
        "통계적 근거가 된다[/bold]\n"
    )

    # Part 2: Rank Family 비교
    family_table = Table(title="Experiment #18b: Rank Family Comparison")
    for col in ("Concept", "N", "Mean Gap", "Std Dev", "양수 비율"):
        family_table.add_column(col)

    family_rows = []
    for concept, gaps in gaps_by_concept.items():
        mean_gap = statistics.mean(gaps)
        std = statistics.stdev(gaps) if len(gaps) > 1 else 0.0
        positive_ratio = f"{sum(1 for g in gaps if g > 0)}/{len(gaps)}"
        family_rows.append((concept, len(gaps), mean_gap, std, positive_ratio))

    family_rows.sort(key=lambda r: -r[2])
    for concept, n, mean_gap, std, positive_ratio in family_rows:
        family_table.add_row(concept, str(n), f"{mean_gap:+.4f}", f"{std:.4f}", positive_ratio)

    console.print(family_table)


if __name__ == "__main__":
    main()
