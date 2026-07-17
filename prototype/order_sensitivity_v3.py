"""Experiment #11: Greedy(assign_scrap) vs Topic-First(assign_scrap_topic_first)의
순서 의존성을 같은 데이터셋·같은 순서 집합으로 비교한다.

Order Sensitivity v2(Experiment #10)는 Greedy 하나만 4가지 순서로 봤다. 이번엔
두 알고리즘을 그룹 순서 2가지 + 랜덤 셔플 N가지에 대해 나란히 돌려서, Topic-First가
가설대로(Root Cause: Island 단위 판단이 local하다) 순서 의존성을 줄이는지 정량적으로
확인한다.
"""

import json
import random
import statistics
from collections import Counter
from itertools import combinations
from typing import Callable

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from world import Island, AssignmentTrace, assign_scrap, assign_scrap_topic_first

console = Console()

RANDOM_SHUFFLE_COUNT = 30

ALGORITHMS: dict[str, Callable[[list[Island], list[float], str, dict], AssignmentTrace]] = {
    "Greedy (assign_scrap)": assign_scrap,
    "Topic-First (assign_scrap_topic_first)": assign_scrap_topic_first,
}


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_dataset(path: str) -> dict[str, dict]:
    with open(path) as f:
        return json.load(f)


def order_grouped(items: list[tuple[str, dict]], island_order: list[str]) -> list[tuple[str, dict]]:
    ordered: list[tuple[str, dict]] = []
    for island_label in island_order:
        ordered += [item for item in items if item[1]["island"] == island_label]
    return ordered


def build_world(
    assign_fn: Callable[[list[Island], list[float], str, dict], AssignmentTrace],
    items: list[tuple[str, dict]],
    vectors: dict[str, list[float]],
    algorithm_config: dict,
) -> list[Island]:
    islands: list[Island] = []
    for key, entry in items:
        assign_fn(islands, vectors[key], entry["text"], algorithm_config)
    return islands


def pairwise_f1(islands: list[Island], text_to_true: dict[str, str]) -> tuple[float, float, float]:
    predicted_island_of: dict[str, int] = {}
    for isl in islands:
        for topic in isl.topics:
            for text in topic.scraps:
                predicted_island_of[text] = isl.id

    all_texts = list(predicted_island_of.keys())
    tp = fp = fn = 0
    for a, b in combinations(all_texts, 2):
        same_pred = predicted_island_of[a] == predicted_island_of[b]
        same_true = text_to_true[a] == text_to_true[b]
        if same_pred and same_true:
            tp += 1
        elif same_pred and not same_true:
            fp += 1
        elif not same_pred and same_true:
            fn += 1
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = 2 * precision * recall / (precision + recall) if (tp + fp) and (tp + fn) else float("nan")
    return precision, recall, f1


def main() -> None:
    load_dotenv()
    config = load_config()
    provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])
    algorithm_config = config["algorithm"]

    dataset = load_dataset("../golden_dataset/threshold/topic/dataset.json")
    base_items = list(dataset.items())

    # 임베딩은 순서·알고리즘과 무관 - 한 번만 계산해서 재사용
    vectors = {key: provider.embed(entry["text"]) for key, entry in base_items}
    text_to_island = {entry["text"]: entry["island"] for _, entry in base_items}

    orderings: dict[str, list[tuple[str, dict]]] = {
        "Backend->AI->Sports": order_grouped(base_items, ["Backend", "AI", "Sports"]),
        "Sports->Backend->AI": order_grouped(base_items, ["Sports", "Backend", "AI"]),
    }
    for seed in range(1, RANDOM_SHUFFLE_COUNT + 1):
        orderings[f"Shuffle(seed={seed})"] = random.Random(seed).sample(base_items, len(base_items))

    detail_table = Table(title="Experiment #11: Order Sensitivity by Algorithm (per-order detail)")
    for col in ("Order", "Algorithm", "Islands", "F1"):
        detail_table.add_column(col)

    results: dict[str, dict[str, list]] = {name: {"f1": [], "islands": []} for name in ALGORITHMS}

    for order_name, items in orderings.items():
        for algo_name, assign_fn in ALGORITHMS.items():
            islands = build_world(assign_fn, items, vectors, algorithm_config)
            _, _, f1 = pairwise_f1(islands, text_to_island)
            results[algo_name]["f1"].append(f1)
            results[algo_name]["islands"].append(len(islands))
            detail_table.add_row(order_name, algo_name, str(len(islands)), f"{f1:.3f}")

    console.print(detail_table)

    summary_table = Table(title=f"Experiment #11: Summary ({len(orderings)} orderings)")
    for col in ("Algorithm", "F1 mean", "F1 std", "F1 min", "F1 max", "Islands (mode / range)"):
        summary_table.add_column(col)

    for algo_name, data in results.items():
        f1_values = data["f1"]
        island_counts = data["islands"]
        island_mode = Counter(island_counts).most_common(1)[0]
        summary_table.add_row(
            algo_name,
            f"{statistics.mean(f1_values):.3f}",
            f"{statistics.stdev(f1_values):.3f}",
            f"{min(f1_values):.3f}",
            f"{max(f1_values):.3f}",
            f"{island_mode[0]} ({island_mode[1]}/{len(island_counts)}) / {min(island_counts)}-{max(island_counts)}",
        )

    console.print(summary_table)


if __name__ == "__main__":
    main()
