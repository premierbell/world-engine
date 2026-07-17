"""Step 5 Order Sensitivity Test v2: 그룹 순서(Backend->AI->Sports, Sports->Backend->AI)와
랜덤 셔플(seed 42, 777) 각각에 대해 Island 개수/구성/Pairwise F1을 비교한다.

Pairwise F1: 모든 쌍에 대해 "예측이 같은 Island로 뒀는가"와 "실제로 같은 도메인인가"를
비교한 Precision/Recall/F1 - Threshold Sweep(#6/#7)에서 쓴 F1과 같은 개념을, 이번엔
정적 유사도가 아니라 실제 Online Clustering 결과에 적용한다.
"""

import json
import random
from collections import Counter
from itertools import combinations

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from world import Island, assign_scrap

console = Console()

ISLAND_THRESHOLD = 0.24  # 현재 baseline


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
    items: list[tuple[str, dict]], vectors: dict[str, list[float]], algorithm_config: dict, island_threshold: float
) -> list[Island]:
    config = dict(algorithm_config, island_threshold=island_threshold)
    islands: list[Island] = []
    for key, entry in items:
        assign_scrap(islands, vectors[key], entry["text"], config)
    return islands


def composition(island: Island, text_to_label: dict[str, str]) -> str:
    counts = Counter(text_to_label[text] for topic in island.topics for text in topic.scraps)
    return ", ".join(f"{label}={n}" for label, n in counts.most_common())


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

    # 임베딩은 순서와 무관 - 한 번만 계산해서 재사용
    vectors = {key: provider.embed(entry["text"]) for key, entry in base_items}
    text_to_island = {entry["text"]: entry["island"] for _, entry in base_items}

    orderings: dict[str, list[tuple[str, dict]]] = {
        "Backend->AI->Sports": order_grouped(base_items, ["Backend", "AI", "Sports"]),
        "Sports->Backend->AI": order_grouped(base_items, ["Sports", "Backend", "AI"]),
        "Shuffle(seed=42)": random.Random(42).sample(base_items, len(base_items)),
        "Shuffle(seed=777)": random.Random(777).sample(base_items, len(base_items)),
    }

    table = Table(title=f"Order Sensitivity v2 (island_threshold={ISLAND_THRESHOLD:.2f})")
    for col in ("Order", "Islands", "Precision", "Recall", "F1", "Composition"):
        table.add_column(col)

    for name, items in orderings.items():
        islands = build_world(items, vectors, algorithm_config, ISLAND_THRESHOLD)
        precision, recall, f1 = pairwise_f1(islands, text_to_island)
        composition_text = "\n".join(f"#{isl.id}: {composition(isl, text_to_island)}" for isl in islands)
        table.add_row(name, str(len(islands)), f"{precision:.3f}", f"{recall:.3f}", f"{f1:.3f}", composition_text)

    console.print(table)


if __name__ == "__main__":
    main()
