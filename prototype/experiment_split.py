"""Experiment #23: Split Prototype - Merge + Split Full Cycle.

Finding #003(Merge-only는 Online 단계에서 이미 과병합된 Island를 고치지 못한다)
이후 처음 만든 Split(`find_split_candidates` + `apply_split`)을 AI Researcher
데이터셋에 실제로 적용해본다. Merge까지 끝난 상태에서 Split을 추가로 돌렸을 때
Topic Duplication Rate가 더 내려가는지 확인하고, Backend User(원래 Merge만으로
이미 잘 정리됐던 케이스)에도 돌려서 Split이 불필요한 곳까지 건드리지 않는지
같이 확인한다 - Split은 Merge보다 훨씬 보수적으로 설계됐어야 하므로, "아무것도
안 하는 게 맞는 곳에서는 정말 아무것도 안 하는지"도 이 실험의 일부다.
"""

import json
import sys
from collections import defaultdict

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from world import Island, apply_split, assign_scrap, find_split_candidates, night_batch

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


def main() -> None:
    load_dotenv()
    config = load_config()
    embedding_provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])

    path = sys.argv[1] if len(sys.argv) > 1 else "../experiments/virtual_users/ai_researcher.json"
    user = load_virtual_user(path)
    console.print(f"[bold]{user['user']}[/bold]: {user['persona']}\n")

    scraps = sorted(user["scraps"], key=lambda s: s["day"])
    text_to_ground_truth = {s["text"]: s["topic"] for s in scraps}
    vectors = {s["text"]: embedding_provider.embed(s["text"]) for s in scraps}

    # Stage 1: Online-only
    islands: list[Island] = []
    checkpoints = sorted({s["day"] for s in scraps})
    checkpoint_idx = 0
    for i, scrap in enumerate(scraps):
        assign_scrap(islands, vectors[scrap["text"]], scrap["text"], config["algorithm"])
        is_last_of_checkpoint = (i + 1 == len(scraps)) or (scraps[i + 1]["day"] != scrap["day"])
        if is_last_of_checkpoint and scrap["day"] == checkpoints[checkpoint_idx]:
            checkpoint_idx += 1
    online_only = islands

    # Stage 2: + Night Batch (Merge)
    merged = night_batch(list(online_only), vectors)

    # Stage 3: + Split (Merge 결과에 이어서 적용)
    candidates = find_split_candidates(merged, vectors)
    split = apply_split(merged, candidates, vectors)

    table = Table(title="Experiment #23: Online-only -> +Merge -> +Split")
    for col in ("Stage", "Island 수", "Topic 중복률", "중복/전체"):
        table.add_column(col)
    for name, isl_list in (("Online-only", online_only), ("+ Night Batch (Merge)", merged), ("+ Split", split)):
        rate, duplicated, total = topic_duplication_rate(isl_list, text_to_ground_truth)
        table.add_row(name, str(len(isl_list)), f"{rate:.1%}", f"{duplicated}/{total}")
    console.print(table)

    detail_table = Table(title="+ Split: Island 구성")
    for col in ("Island", "포함된 실제 주제", "다양성"):
        detail_table.add_column(col)
    for isl in split:
        topics_in_island = {text_to_ground_truth[text] for topic in isl.topics for text in topic.scraps}
        detail_table.add_row(f"#{isl.id}", ", ".join(sorted(topics_in_island)), str(len(topics_in_island)))
    console.print(detail_table)

    if not candidates:
        console.print("\n[bold]Split 후보 없음 - 이미 충분히 순수하거나 쪼갤 만한 구조가 없음[/bold]")


if __name__ == "__main__":
    main()
