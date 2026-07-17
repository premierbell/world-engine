"""Growth Simulator: Virtual User의 시간 축 스크랩 궤적을 재생하며 세계가 어떻게
자라는지 관찰한다.

지금까지의 실험(Threshold Dataset, Semantic Atlas, Golden Dataset)은 전부 "정적인
스냅샷"이었다 - 미리 정해둔 항목들을 한 번에(또는 순서만 바꿔서) 넣고 결과를 봤다.
이 스크립트는 다르다: `experiments/virtual_users/*.json`에 정의된 사용자의 스크랩을
실제 저장 순서(day)대로 하나씩 흘려보내면서, 각 day 체크포인트마다 세계의 스냅샷
(Island 개수/구성, 각 Topic의 Label)을 찍는다.

Hybrid Architecture(Step 5.5)의 Night Batch는 아직 구현되지 않았다 - 이 시뮬레이션은
순수 Online Greedy(`assign_scrap`)만 사용한다. 따라서 Finding #001의 순서 의존성이
그대로 나타날 수 있다는 걸 전제로 결과를 읽어야 한다 - 이건 시뮬레이터의 결함이
아니라 Night Batch가 왜 필요한지를 보여주는 관찰 대상이다.

사용법: uv run python simulate_growth.py ../experiments/virtual_users/backend_developer.json
"""

import json
import sys
from collections import Counter, defaultdict

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from label_generator import OpenAILabelGenerator
from world import Island, assign_scrap


console = Console()


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_virtual_user(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def snapshot(day: int, islands: list[Island], label_generator: OpenAILabelGenerator, text_to_ground_truth: dict[str, str]) -> None:
    table = Table(title=f"Day {day} 스냅샷 — Island {len(islands)}개")
    for col in ("Island", "Topic 수", "Topic 구성(라벨 / 실제 주제 / 크기)"):
        table.add_column(col)

    for island in islands:
        topic_lines = []
        for topic in island.topics:
            label = label_generator.generate(topic.scraps, level="topic")
            ground_truth_counts = Counter(text_to_ground_truth[text] for text in topic.scraps)
            ground_truth = "+".join(f"{name}({n})" for name, n in ground_truth_counts.most_common())
            topic_lines.append(f"{label} / {ground_truth} / {len(topic.scraps)}개")
        table.add_row(f"#{island.id}", str(len(island.topics)), "\n".join(topic_lines))

    console.print(table)

    # Island 하나에 서로 다른 "실제 주제"가 몇 개나 섞여 있는지 - Programming Mega Island 여부 확인용
    diversity_table = Table(title=f"Day {day}: Island별 실제 주제(topic) 다양성")
    for col in ("Island", "포함된 실제 주제", "다양성(고유 주제 수)"):
        diversity_table.add_column(col)
    for island in islands:
        topics_in_island = set()
        for topic in island.topics:
            for text in topic.scraps:
                topics_in_island.add(text_to_ground_truth[text])
        diversity_table.add_row(f"#{island.id}", ", ".join(sorted(topics_in_island)), str(len(topics_in_island)))
    console.print(diversity_table)
    console.print()


def main() -> None:
    if len(sys.argv) < 2:
        console.print("[bold red]사용법: uv run python simulate_growth.py <virtual_user.json 경로>[/bold red]")
        sys.exit(1)

    load_dotenv()
    config = load_config()
    embedding_provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])
    label_generator = OpenAILabelGenerator(model=config["label"]["model"])

    user = load_virtual_user(sys.argv[1])
    scraps = sorted(user["scraps"], key=lambda s: s["day"])
    checkpoints = sorted({s["day"] for s in scraps})

    console.print(f"[bold]{user['user']}[/bold]: {user['persona']}\n")

    text_to_ground_truth = {s["text"]: s["topic"] for s in scraps}
    vectors = {s["text"]: embedding_provider.embed(s["text"]) for s in scraps}

    islands: list[Island] = []
    checkpoint_idx = 0
    for i, scrap in enumerate(scraps):
        assign_scrap(islands, vectors[scrap["text"]], scrap["text"], config["algorithm"])

        is_last_of_checkpoint = (i + 1 == len(scraps)) or (scraps[i + 1]["day"] != scrap["day"])
        if is_last_of_checkpoint and scrap["day"] == checkpoints[checkpoint_idx]:
            snapshot(scrap["day"], islands, label_generator, text_to_ground_truth)
            checkpoint_idx += 1


if __name__ == "__main__":
    main()
