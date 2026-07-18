"""Experiment #24: Topic Graph Reconstruction - Chaining Instability.

Finding #004 이전까지의 흐름(Night Batch v0 Merge-only가 AI Researcher에서
실패 -> Split 추가 -> 오히려 중복 증가 -> Split 직후 재-Merge도 효과 없음)이
Island를 기본 단위로 삼은 것 자체의 한계를 가리켰다. `hybrid_architecture.md`
"Night Batch v2" 절에서 Island 대신 Topic을 기본 단위로 삼는 Topic Graph
Reconstruction(`world.py`의 `topic_graph_reconstruct`)을 설계했다 - 모든 Topic
쌍의 유사도로 그래프를 만들고, threshold 이상이면 edge를 긋고, Connected
Component가 새 Island가 되는 방식(Union-Find).

이 실험은 그 설계를 실제로 검증한다. edge_threshold를 스윕해서 Backend
User(1개 Island가 정답)와 AI Researcher(여러 개가 정답에 가까움, Experiment
#22의 HDBSCAN 진단 참고)를 동시에 만족하는 안정적인 threshold 구간이
있는지 확인한다.
"""

import json
from collections import defaultdict

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from world import assign_scrap, topic_graph_reconstruct

console = Console()

THRESHOLD_SWEEP = [0.24, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_virtual_user(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def dup_rate(islands, text_to_topic: dict[str, str]) -> tuple[int, int]:
    topic_to_islands: dict[str, set[int]] = defaultdict(set)
    for isl in islands:
        for topic in isl.topics:
            for text in topic.scraps:
                topic_to_islands[text_to_topic[text]].add(isl.id)
    duplicated = sum(1 for island_ids in topic_to_islands.values() if len(island_ids) > 1)
    return duplicated, len(topic_to_islands)


def main() -> None:
    load_dotenv()
    config = load_config()
    embedding_provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])

    datasets = [
        "../experiments/virtual_users/backend_developer.json",
        "../experiments/virtual_users/ai_researcher.json",
    ]

    table = Table(title="Experiment #24: Topic Graph edge_threshold Sweep")
    table.add_column("Threshold")
    table.add_column("Backend User (Islands / 중복)")
    table.add_column("AI Researcher (Islands / 중복)")

    per_dataset_scraps = {}
    for path in datasets:
        user = load_virtual_user(path)
        scraps = sorted(user["scraps"], key=lambda s: s["day"])
        text_to_topic = {s["text"]: s["topic"] for s in scraps}
        vectors = {s["text"]: embedding_provider.embed(s["text"]) for s in scraps}
        per_dataset_scraps[path] = (scraps, text_to_topic, vectors)

    for threshold in THRESHOLD_SWEEP:
        row = [f"{threshold:.2f}"]
        for path in datasets:
            scraps, text_to_topic, vectors = per_dataset_scraps[path]
            islands = []
            for s in scraps:
                assign_scrap(islands, vectors[s["text"]], s["text"], config["algorithm"])
            final = topic_graph_reconstruct(islands, vectors, edge_threshold=threshold)
            duplicated, total = dup_rate(final, text_to_topic)
            row.append(f"{len(final)} / {duplicated}/{total}")
        table.add_row(*row)

    console.print(table)
    console.print(
        "\n[bold]안정적인 구간(Backend=1개 유지 + AI Researcher가 여러 개로 갈리면서도 "
        "중복이 낮은 지점)이 있는지 확인 - 없다면 pairwise threshold graph의 "
        "chaining 문제로 해석한다.[/bold]"
    )


if __name__ == "__main__":
    main()
