"""Finding #006 근거: Online 단계에서 Topic 자체가 이미 여러 실제 주제를
섞어서 만들어질 수 있다.

`selective_night_batch`(Night Batch v3, Finding #005 대응)를 AI Researcher에
적용해도 원하는 결과(여러 개로 자연스럽게 갈리며 중복 낮음)가 안 나와서 원인을
추적하다가, Island가 아니라 **Topic 내부**가 이미 오염되어 있다는 걸 발견했다.
지금까지의 모든 Night Batch 버전(v0~v3)은 "Topic은 신뢰할 수 있는 원자
단위"라고 가정했는데 그 가정 자체가 틀렸다는 증거다.
"""

import json
from collections import Counter

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from world import assign_scrap

console = Console()


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_virtual_user(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def main() -> None:
    load_dotenv()
    config = load_config()
    embedding_provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])

    user = load_virtual_user("../experiments/virtual_users/ai_researcher.json")
    scraps = sorted(user["scraps"], key=lambda s: s["day"])
    text_to_topic = {s["text"]: s["topic"] for s in scraps}
    vectors = {s["text"]: embedding_provider.embed(s["text"]) for s in scraps}

    islands = []
    for s in scraps:
        assign_scrap(islands, vectors[s["text"]], s["text"], config["algorithm"])

    table = Table(title="Finding #006: Online Topic 내부의 실제 주제 혼합 여부")
    for col in ("Island", "Topic", "스크랩 수", "실제 주제 구성", "오염 여부"):
        table.add_column(col)

    contaminated_count = 0
    total_topics = 0
    for isl in islands:
        for topic in isl.topics:
            total_topics += 1
            composition = Counter(text_to_topic[text] for text in topic.scraps)
            is_contaminated = len(composition) > 1
            if is_contaminated:
                contaminated_count += 1
            composition_str = ", ".join(f"{name}:{n}" for name, n in composition.most_common())
            marker = "[bold red]오염됨[/bold red]" if is_contaminated else "순수"
            table.add_row(f"#{isl.id}", str(topic.id), str(len(topic.scraps)), composition_str, marker)

    console.print(table)
    console.print(
        f"\n[bold]{total_topics}개 Topic 중 {contaminated_count}개({contaminated_count/total_topics:.0%})가 "
        f"2개 이상의 실제 주제를 섞고 있음 - Night Batch가 Topic을 통째로 옮기는 연산만으로는 "
        f"이 오염을 고칠 수 없다.[/bold]"
    )


if __name__ == "__main__":
    main()
