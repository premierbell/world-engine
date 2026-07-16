"""Step 5 Order Sensitivity Test: 같은 island_threshold로 입력 순서만 바꿔가며
Online Greedy Clustering이 순서에 얼마나 민감한지 확인한다.

Experiment #8(Online Threshold Sweep)에서 "언더분리 -> 오버분리"로 바로 넘어가고
안정적인 3-Island 구간이 없다는 걸 발견했다. 이게 threshold 문제가 아니라 Greedy
Assignment의 순서 의존성 때문일 수 있다는 가설을 검증한다.
"""

import json
import random
from collections import Counter

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from world import Island, assign_scrap

console = Console()

SEEDS = [1, 2, 3, 4, 5]
ISLAND_THRESHOLD_CANDIDATES = [0.24, 0.28]


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_dataset(path: str) -> dict[str, dict]:
    with open(path) as f:
        return json.load(f)


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


def main() -> None:
    load_dotenv()
    config = load_config()
    provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])
    algorithm_config = config["algorithm"]

    dataset = load_dataset("../golden_dataset/threshold/topic/dataset.json")
    base_items = list(dataset.items())

    # 임베딩은 입력 순서와 무관 - 한 번만 계산해서 모든 seed/threshold에 재사용
    vectors = {key: provider.embed(entry["text"]) for key, entry in base_items}
    text_to_island = {entry["text"]: entry["island"] for _, entry in base_items}

    for threshold in ISLAND_THRESHOLD_CANDIDATES:
        table = Table(title=f"Order Sensitivity (island_threshold={threshold:.2f})")
        for col in ("Seed", "Islands", "Composition"):
            table.add_column(col)
        for seed in SEEDS:
            items = list(base_items)
            random.Random(seed).shuffle(items)
            islands = build_world(items, vectors, algorithm_config, threshold)
            composition_text = "\n".join(f"#{isl.id}: {composition(isl, text_to_island)}" for isl in islands)
            table.add_row(str(seed), str(len(islands)), composition_text)
        console.print(table)


if __name__ == "__main__":
    main()
