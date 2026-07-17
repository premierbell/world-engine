"""Step 6A: Topic Label Generation.

golden_dataset/threshold/topic/dataset.json(35개, 7개 Topic: Spring/JPA, Kafka,
Redis, LLM, RAG, Baseball, Football)로 world를 만든 뒤, 실제로 형성된 각 Topic의
스크랩들을 `LabelGenerator`에 넘겨 AI가 붙이는 이름표를 확인한다. 원래 golden
dataset에 있던 사람 라벨(예: "Spring/JPA")과 나란히 비교해서 감으로 품질을 본다 -
정답이 있는 게 아니라 "말이 되는가"를 사람이 눈으로 확인하는 단계다.
"""

import json
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


def load_dataset(path: str) -> dict[str, dict]:
    with open(path) as f:
        return json.load(f)


def main() -> None:
    load_dotenv()
    config = load_config()
    embedding_provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])
    label_generator = OpenAILabelGenerator(model=config["label"]["model"])

    dataset = load_dataset("../golden_dataset/threshold/topic/dataset.json")
    items = list(dataset.items())
    vectors = {key: embedding_provider.embed(entry["text"]) for key, entry in items}
    text_to_ground_truth_topic = {entry["text"]: entry["topic"] for _, entry in items}

    islands: list[Island] = []
    for key, entry in items:
        assign_scrap(islands, vectors[key], entry["text"], config["algorithm"])

    table = Table(title="Step 6A: Topic Label Generation")
    for col in ("Island", "Topic 크기", "Ground Truth(다수결)", "AI 생성 Label"):
        table.add_column(col)

    for island in islands:
        for topic in island.topics:
            generated_label = label_generator.generate(topic.scraps, level="topic")
            ground_truth_counts = Counter(text_to_ground_truth_topic[text] for text in topic.scraps)
            ground_truth = ", ".join(f"{name}({n})" for name, n in ground_truth_counts.most_common())
            table.add_row(f"#{island.id}", str(len(topic.scraps)), ground_truth, generated_label)

    console.print(table)


if __name__ == "__main__":
    main()
