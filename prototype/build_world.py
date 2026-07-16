"""Step 5: 실제 Island/Topic 편입 로직을 돌려본다 (Instrumented).

golden_dataset/threshold/topic/dataset.json(35개, 정답 라벨 있음)을 무작위 순서로
하나씩 흘려보내며 World Engine이 실제로 Backend/AI/Sports 섬과 그 안의 Topic을
스스로 재구성하는지 확인한다. 모든 결정(Island별 유사도, threshold, MERGE/CREATE,
center drift)을 로그로 남겨 "왜 하나의 Island로 뭉쳤는가"를 진단한다.
"""

import json
import random

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.tree import Tree

from embedding_provider import OpenAIEmbeddingProvider
from world import AssignmentTrace, Island, assign_scrap

console = Console()


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_dataset(path: str) -> dict[str, dict]:
    with open(path) as f:
        return json.load(f)


def print_step(step: int, trace: AssignmentTrace) -> None:
    console.print(f"\n[bold cyan]Processing #{step}[/bold cyan]")
    console.print(f"Input: {trace.text}")

    if trace.island_similarities:
        console.print("Similarity to every Island:")
        for island_id, sim in sorted(trace.island_similarities, key=lambda pair: -pair[1]):
            marker = " <- nearest" if island_id == trace.chosen_island_id else ""
            console.print(f"  Island #{island_id}: {sim:.4f}{marker}")

    console.print(f"Threshold: {trace.island_threshold:.2f}")
    console.print(f"Decision: [bold]{trace.island_decision}[/bold] -> Island #{trace.chosen_island_id}")

    if trace.island_decision == "MERGE":
        console.print(f"Identity Stability: {trace.identity_stability:.4f}")
        console.print(
            f"Topic: #{trace.topic_id} (sim={trace.topic_similarity:.4f}, {trace.topic_decision})"
        )


def print_summary(traces: list[AssignmentTrace], islands: list[Island]) -> None:
    merges = sum(1 for t in traces if t.island_decision == "MERGE")
    creates = sum(1 for t in traces if t.island_decision == "CREATE_ISLAND")
    chosen_sims = [t.chosen_similarity for t in traces if t.chosen_similarity is not None]

    console.print("\n[bold yellow]Summary[/bold yellow]")
    console.print(f"Island Count: {len(islands)}")
    console.print(f"Merge: {merges}   Create: {creates}")
    if chosen_sims:
        avg = sum(chosen_sims) / len(chosen_sims)
        console.print(
            f"Nearest-similarity across all steps -> avg={avg:.4f}  max={max(chosen_sims):.4f}  min={min(chosen_sims):.4f}"
        )


def print_world(islands: list[Island]) -> None:
    tree = Tree("🌍 World")
    for island in islands:
        count = sum(len(t.scraps) for t in island.topics)
        island_node = tree.add(f"🏝 Island {island.id} ({count} scraps)")
        for topic in island.topics:
            topic_node = island_node.add(f"🏢 Topic {topic.id} ({len(topic.scraps)})")
            for text in topic.scraps:
                topic_node.add(text)
    console.print(tree)


def main() -> None:
    load_dotenv()
    config = load_config()
    provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])
    algorithm_config = config["algorithm"]

    dataset = load_dataset("../golden_dataset/threshold/topic/dataset.json")
    items = list(dataset.items())
    random.Random(42).shuffle(items)

    islands: list[Island] = []
    traces: list[AssignmentTrace] = []
    for step, (key, entry) in enumerate(items, start=1):
        vector = provider.embed(entry["text"])
        trace = assign_scrap(islands, vector, entry["text"], algorithm_config)
        traces.append(trace)
        print_step(step, trace)

    print_summary(traces, islands)
    print_world(islands)


if __name__ == "__main__":
    main()
