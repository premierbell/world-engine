"""Experiment #25: Topic-level HDBSCAN - Two Variants, Both Fall Short.

Finding #004(Pairwise Threshold Graph의 chaining)에 대한 대응으로, Union-Find를
Topic-level HDBSCAN으로 교체하는 두 가지 변형을 시도한다:

- 변형 A (`topic_graph_reconstruct_hdbscan`): Topic의 center_vector를 직접
  HDBSCAN으로 클러스터링.
- 변형 B (`topic_graph_reconstruct_scrap_informed`): 이미 검증된 scrap 레벨
  HDBSCAN(Experiment #12/#15/#22)의 라벨을 참고해서 Topic을 재그룹화.

둘 다 Backend User(Online 결과가 이미 좋은 케이스, 1개 Island가 정답에
가까움)와 AI Researcher(과병합, 여러 개가 정답에 가까움)를 동시에 만족하는지
확인한다. 결과: 둘 다 실패 - Finding #005(Aggregation Level Trade-off) 참고.
"""

import json
from collections import defaultdict

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from world import assign_scrap, topic_graph_reconstruct_hdbscan, topic_graph_reconstruct_scrap_informed

console = Console()

VARIANT_A_SWEEP = [2, 3, 4, 5, 6]
VARIANT_B_SWEEP = [3, 4, 5, 6, 8, 10]


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


def build_online_islands(scraps, vectors, algorithm_config):
    islands = []
    for s in scraps:
        assign_scrap(islands, vectors[s["text"]], s["text"], algorithm_config)
    return islands


def main() -> None:
    load_dotenv()
    config = load_config()
    embedding_provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])

    datasets = {}
    for path in [
        "../experiments/virtual_users/backend_developer.json",
        "../experiments/virtual_users/ai_researcher.json",
    ]:
        user = load_virtual_user(path)
        scraps = sorted(user["scraps"], key=lambda s: s["day"])
        text_to_topic = {s["text"]: s["topic"] for s in scraps}
        vectors = {s["text"]: embedding_provider.embed(s["text"]) for s in scraps}
        datasets[user["user"]] = (scraps, text_to_topic, vectors)

    table_a = Table(title="Experiment #25 - Variant A: Topic-centroid HDBSCAN")
    table_a.add_column("min_cluster_size")
    for name in datasets:
        table_a.add_column(name)
    for mcs in VARIANT_A_SWEEP:
        row = [str(mcs)]
        for name, (scraps, text_to_topic, vectors) in datasets.items():
            islands = build_online_islands(scraps, vectors, config["algorithm"])
            final = topic_graph_reconstruct_hdbscan(islands, vectors, min_cluster_size=mcs)
            duplicated, total = dup_rate(final, text_to_topic)
            row.append(f"{len(final)} islands, {duplicated}/{total}")
        table_a.add_row(*row)
    console.print(table_a)

    table_b = Table(title="Experiment #25 - Variant B: Scrap-informed Topic Regroup")
    table_b.add_column("min_cluster_size")
    for name in datasets:
        table_b.add_column(name)
    for mcs in VARIANT_B_SWEEP:
        row = [str(mcs)]
        for name, (scraps, text_to_topic, vectors) in datasets.items():
            islands = build_online_islands(scraps, vectors, config["algorithm"])
            final = topic_graph_reconstruct_scrap_informed(islands, vectors, min_cluster_size=mcs)
            duplicated, total = dup_rate(final, text_to_topic)
            row.append(f"{len(final)} islands, {duplicated}/{total}")
        table_b.add_row(*row)
    console.print(table_b)

    console.print(
        "\n[bold]기준: Backend User는 1개/0%에 가까울수록, AI Researcher는 여러 개면서 "
        "중복이 낮을수록 좋다. 두 조건을 동시에 만족하는 설정이 있는지 확인 - "
        "Experiment #25 결과로는 없었다(Finding #005).[/bold]"
    )


if __name__ == "__main__":
    main()
