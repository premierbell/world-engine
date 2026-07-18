"""Experiment #21: Night Batch Before/After Comparison.

Experiment #20에서 확인한 "Fragmentation of User Interest"(Online-only로는
같은 실제 주제가 여러 Island에 중복 등장)를 Night Batch(v0, Merge-only)가
실제로 줄이는지 검증한다. 같은 Virtual User Dataset(`backend_developer.json`)을
두 갈래로 처리한다:

- Online-only: Experiment #20과 동일 - assign_scrap만 사용.
- Online + Night Batch: 매 day 체크포인트가 끝날 때마다 night_batch()를
  한 번씩 실행("낮에는 빠른 결정, 밤에는 세계 정리" 주기를 그대로 재현).

지표는 Experiment #20에서 이미 쓴 것을 그대로 재사용한다 - Island 수, Topic
중복률(distinct 실제 주제 중 2개 이상 Island에 걸친 비율).
"""

import json
import sys
from collections import defaultdict

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from world import Island, assign_scrap, night_batch

console = Console()


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_virtual_user(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def topic_duplication_rate(islands: list[Island], text_to_ground_truth: dict[str, str]) -> tuple[float, int, int]:
    topic_to_islands: dict[str, set[int]] = defaultdict(set)
    for isl in islands:
        for topic in isl.topics:
            for text in topic.scraps:
                topic_to_islands[text_to_ground_truth[text]].add(isl.id)
    duplicated = sum(1 for island_ids in topic_to_islands.values() if len(island_ids) > 1)
    total = len(topic_to_islands)
    return duplicated / total if total else 0.0, duplicated, total


def run(scraps: list[dict], vectors: dict[str, list[float]], algorithm_config: dict, use_night_batch: bool) -> list[Island]:
    islands: list[Island] = []
    checkpoints = sorted({s["day"] for s in scraps})
    checkpoint_idx = 0
    for i, scrap in enumerate(scraps):
        assign_scrap(islands, vectors[scrap["text"]], scrap["text"], algorithm_config)
        is_last_of_checkpoint = (i + 1 == len(scraps)) or (scraps[i + 1]["day"] != scrap["day"])
        if is_last_of_checkpoint and scrap["day"] == checkpoints[checkpoint_idx]:
            if use_night_batch:
                islands = night_batch(islands, vectors)
            checkpoint_idx += 1
    return islands


def main() -> None:
    load_dotenv()
    config = load_config()
    embedding_provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])

    path = sys.argv[1] if len(sys.argv) > 1 else "../experiments/virtual_users/backend_developer.json"
    user = load_virtual_user(path)
    console.print(f"[bold]{user['user']}[/bold]: {user['persona']}\n")
    scraps = sorted(user["scraps"], key=lambda s: s["day"])
    text_to_ground_truth = {s["text"]: s["topic"] for s in scraps}
    vectors = {s["text"]: embedding_provider.embed(s["text"]) for s in scraps}

    online_only = run(scraps, vectors, config["algorithm"], use_night_batch=False)
    with_night_batch = run(scraps, vectors, config["algorithm"], use_night_batch=True)

    table = Table(title="Experiment #21: Online-only vs Online + Night Batch (Day 30 최종 상태)")
    for col in ("", "Island 수", "Topic 중복률", "중복/전체 실제 주제"):
        table.add_column(col)

    for name, islands in (("Online-only", online_only), ("Online + Night Batch", with_night_batch)):
        rate, duplicated, total = topic_duplication_rate(islands, text_to_ground_truth)
        table.add_row(name, str(len(islands)), f"{rate:.1%}", f"{duplicated}/{total}")

    console.print(table)

    detail_table = Table(title="Online + Night Batch: Island 구성")
    for col in ("Island", "포함된 실제 주제", "다양성"):
        detail_table.add_column(col)
    for isl in with_night_batch:
        topics_in_island = {text_to_ground_truth[text] for topic in isl.topics for text in topic.scraps}
        detail_table.add_row(f"#{isl.id}", ", ".join(sorted(topics_in_island)), str(len(topics_in_island)))
    console.print(detail_table)


if __name__ == "__main__":
    main()
