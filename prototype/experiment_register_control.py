"""Experiment #16: Register Control.

Experiment #15의 Sports+Finance 병합은 Hypothesis(원인 미확정)였다 — register
(뉴스 기사체) 때문일 수도, 실제 의미적 근접성일 수도 있다는 두 가능성이
`docs/algorithm_limitations.md` Finding #002 Evidence 4에 남아 있었다.

같은 24개 사실(Sports 12, Finance 12)을 4가지 register(뉴스/블로그/위키/요약문)로
각각 다시 써서 동일 코퍼스를 4벌 만들고, register별로 Sports-Finance 관계가
유지되는지 비교한다. 뉴스 기사체에서만 붙고 다른 register에서는 떨어진다면
register가 원인이고, 모든 register에서 계속 붙는다면 실제 의미적 근접성일
가능성이 커진다(`docs/evaluation_metrics.md`의 Controlled vs Natural Corpus
설계를 실제로 적용하는 첫 실험).
"""

import json
from collections import defaultdict
from itertools import combinations

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

DATASET_PATH = "../golden_dataset/register_control/dataset.json"
REGISTERS = ["news", "blog", "wiki", "summary"]


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


def main() -> None:
    load_dotenv()
    config = load_config()
    provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])

    dataset = load_dataset(DATASET_PATH)
    items = list(dataset.items())
    vectors = {key: provider.embed(entry["text"]) for key, entry in items}

    summary_table = Table(title="Experiment #16: Register Control - Sports vs Finance by Register")
    for col in ("Register", "Sports 내부", "Finance 내부", "Sports↔Finance", "Gap(최소내부-교차)", "HDBSCAN 결과"):
        summary_table.add_column(col)

    gaps: dict[str, float] = {}

    for register in REGISTERS:
        subset = [(key, entry) for key, entry in items if entry["register"] == register]
        sports_vecs = [vectors[key] for key, entry in subset if entry["island"] == "Sports"]
        finance_vecs = [vectors[key] for key, entry in subset if entry["island"] == "Finance"]

        sports_internal = avg_similarity(sports_vecs, sports_vecs, same_group=True)
        finance_internal = avg_similarity(finance_vecs, finance_vecs, same_group=True)
        cross = avg_similarity(sports_vecs, finance_vecs, same_group=False)
        gap = min(sports_internal, finance_internal) - cross
        gaps[register] = gap

        keys = [key for key, _ in subset]
        matrix = normalize(np.array([vectors[k] for k in keys]))
        labels = HDBSCAN(min_cluster_size=3, min_samples=1, metric="euclidean", copy=True).fit_predict(matrix)
        island_of = {key: entry["island"] for key, entry in subset}
        cluster_islands: dict[int, set[str]] = defaultdict(set)
        for key, label in zip(keys, labels):
            cluster_islands[int(label)].add(island_of[key])
        merged = any(len(islands) > 1 for label, islands in cluster_islands.items() if label != -1)
        n_clusters = len({l for l in labels if l != -1})
        hdbscan_result = f"병합됨 ({n_clusters}개 cluster)" if merged else f"분리됨 ({n_clusters}개 cluster)"

        summary_table.add_row(
            register, f"{sports_internal:.3f}", f"{finance_internal:.3f}", f"{cross:.3f}", f"{gap:.3f}", hdbscan_result
        )

    console.print(summary_table)

    gap_values = list(gaps.values())
    gap_spread = max(gap_values) - min(gap_values)
    console.print(
        f"\n[bold]Gap range: {min(gap_values):.3f} ({min(gaps, key=gaps.get)}) ~ "
        f"{max(gap_values):.3f} ({max(gaps, key=gaps.get)}), spread={gap_spread:.3f}[/bold]"
    )


if __name__ == "__main__":
    main()
