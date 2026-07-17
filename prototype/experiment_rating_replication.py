"""Experiment #19: Rating Corpus Replication.

Experiment #18에서 "Rank"는 N=1(+0.031)에서 N=20(-0.0076, 95% CI가 0을 포함)
으로 확장하자 재현에 실패했다. 같은 Rank Family 비교에서 우연히 발견된
"Rating"(N=5, +0.0768, 4/5 양수)이 새 후보로 떠올랐지만, 이것도 Rank와
똑같이 소규모 표본에서 나온 신호였다 — `docs/algorithm_limitations.md`
Finding #002의 "Candidate Hypotheses (Unvalidated)"에 Status: UNVALIDATED로
남아 있었다.

이 실험은 Rating 개념을 25가지 phrasing(N=25)으로 확장해서 Rank와 똑같은
방식(mean/std/95% CI)으로 재현성을 검증한다. Rank가 겪은 함정(소규모 표본
신호가 노이즈였음)을 그대로 반복하는지, 아니면 이번엔 실제로 재현되는지
확인하는 것이 목표다.
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
RATING_DATASET_PATH = "../golden_dataset/rating_replication/dataset.json"


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
    margin = 1.96 * stdev / (len(values) ** 0.5)
    return mean - margin, mean + margin


def main() -> None:
    load_dotenv()
    config = load_config()
    provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])

    atlas = load_dataset(ATLAS_DATASET_PATH)
    atlas_items = list(atlas.items())
    atlas_vectors = {key: provider.embed(entry["text"]) for key, entry in atlas_items}
    vectors_by_island: dict[str, list[list[float]]] = defaultdict(list)
    for key, entry in atlas_items:
        vectors_by_island[entry["island"]].append(atlas_vectors[key])
    island_centroids = {isl: centroid(vecs) for isl, vecs in vectors_by_island.items()}

    rating = load_dataset(RATING_DATASET_PATH)
    rating_items = list(rating.items())
    probe_vectors = {key: provider.embed(entry["text"]) for key, entry in rating_items}

    gaps = [specificity_gap(probe_vectors[key], island_centroids) for key, _ in rating_items]
    n = len(gaps)
    ci_low, ci_high = confidence_interval_95(gaps)

    detail_table = Table(title=f"Experiment #19: Rating Corpus Detail (N={n})")
    for col in ("Probe", "Sports", "Finance", "Gap"):
        detail_table.add_column(col)
    for key, entry in rating_items:
        sim_sports = cosine_similarity(probe_vectors[key], island_centroids["Sports"])
        sim_finance = cosine_similarity(probe_vectors[key], island_centroids["Finance"])
        gap = specificity_gap(probe_vectors[key], island_centroids)
        detail_table.add_row(entry["text"][:40], f"{sim_sports:.3f}", f"{sim_finance:.3f}", f"{gap:+.4f}")
    console.print(detail_table)

    summary_table = Table(title=f"Experiment #19: Rating Corpus Replication (N={n})")
    for col in ("Metric", "Value"):
        summary_table.add_column(col)
    summary_table.add_row("Mean Specificity Gap", f"{statistics.mean(gaps):+.4f}")
    summary_table.add_row("Std Dev", f"{statistics.stdev(gaps):.4f}")
    summary_table.add_row("Min / Max", f"{min(gaps):+.4f} / {max(gaps):+.4f}")
    summary_table.add_row("95% CI", f"[{ci_low:+.4f}, {ci_high:+.4f}]")
    summary_table.add_row("양수 비율", f"{sum(1 for g in gaps if g > 0)}/{n}")
    console.print(summary_table)

    verdict = "0을 포함하지 않음 -> 재현 성공 (Evidence 승격 후보)" if ci_low > 0 or ci_high < 0 else "0을 포함함 -> 재현 실패"
    console.print(f"\n[bold]95% CI 판정: {verdict}[/bold]")

    # Rank(Experiment #18)와 나란히 비교
    compare_table = Table(title="Experiment #19: Rank vs Rating 재현성 비교")
    for col in ("Concept", "N", "Mean Gap", "95% CI", "판정"):
        compare_table.add_column(col)
    compare_table.add_row("Rank (Experiment #18)", "20", "-0.0076", "[-0.0360, +0.0207]", "재현 실패")
    compare_table.add_row(
        "Rating (Experiment #19)",
        str(n),
        f"{statistics.mean(gaps):+.4f}",
        f"[{ci_low:+.4f}, {ci_high:+.4f}]",
        "재현 성공" if (ci_low > 0 or ci_high < 0) else "재현 실패",
    )
    console.print(compare_table)


if __name__ == "__main__":
    main()
