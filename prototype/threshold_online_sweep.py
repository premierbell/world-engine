"""Step 5 Online Threshold Sweep: island_threshold를 바꿔가며 실제 온라인 알고리즘으로
Backend/AI가 언제부터 분리되기 시작하는지, 그리고 언제부터 과분리(Over Segmentation)가
시작되는지를 찾는다.

주의: Experiment #6/#7의 Threshold Sweep은 정적 pairwise 유사도 기준이었다.
Identity/Growth 분리로 알고리즘 자체가 바뀌었으므로, 이 온라인 sweep 결과를 새 기준으로
삼는다 - 임베딩은 threshold와 무관하므로 한 번만 계산해서 모든 threshold에 재사용한다.
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

ISLAND_THRESHOLDS = [0.24, 0.26, 0.28, 0.30, 0.32, 0.34]


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_dataset(path: str) -> dict[str, dict]:
    with open(path) as f:
        return json.load(f)


def build_world(
    items: list[tuple[str, dict]], vectors: dict[str, list[float]], algorithm_config: dict, island_threshold: float
) -> tuple[list[Island], int, int]:
    config = dict(algorithm_config, island_threshold=island_threshold)
    islands: list[Island] = []
    merges = creates = 0
    for key, entry in items:
        trace = assign_scrap(islands, vectors[key], entry["text"], config)
        if trace.island_decision == "MERGE":
            merges += 1
        else:
            creates += 1
    return islands, merges, creates


def composition(island: Island, text_to_label: dict[str, str]) -> str:
    counts = Counter(text_to_label[text] for topic in island.topics for text in topic.scraps)
    return ", ".join(f"{label}={n}" for label, n in counts.most_common())


def main() -> None:
    load_dotenv()
    config = load_config()
    provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])
    algorithm_config = config["algorithm"]

    dataset = load_dataset("../golden_dataset/threshold/topic/dataset.json")
    items = list(dataset.items())
    random.Random(42).shuffle(items)

    # 임베딩은 threshold와 무관 - 한 번만 계산해서 모든 threshold에서 재사용
    vectors = {key: provider.embed(entry["text"]) for key, entry in items}
    text_to_island = {entry["text"]: entry["island"] for _, entry in items}

    table = Table(title="Online Island Threshold Sweep (topic_focused dataset)")
    for col in ("Threshold", "Islands", "Merge", "Create", "Composition"):
        table.add_column(col)

    for threshold in ISLAND_THRESHOLDS:
        islands, merges, creates = build_world(items, vectors, algorithm_config, threshold)
        composition_text = "\n".join(f"#{isl.id}: {composition(isl, text_to_island)}" for isl in islands)
        table.add_row(f"{threshold:.2f}", str(len(islands)), str(merges), str(creates), composition_text)

    console.print(table)


if __name__ == "__main__":
    main()
