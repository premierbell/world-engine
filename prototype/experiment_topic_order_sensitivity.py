"""Experiment #27: Topic-level Order Sensitivity Test.

Finding #006(Topic 오염은 Online 단계에서 시작된다)에서 제기된 질문 — "Finding
#001의 순서 의존성 패턴이 Island뿐 아니라 Topic 형성에도 처음부터 있었던 게
아닐까?" — 를 Experiment #9/#10과 같은 방법론(같은 데이터, 순서만 바꿔서 반복
실행)으로 직접 검증한다.

이 실험에서 Topic Purity(evaluation_metrics.md TODO)를 처음으로 정의하고
측정한다: 한 Topic 내부 스크랩 중 다수결 실제 주제가 차지하는 비율을, 전체
스크랩 수로 가중平균한 값.
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

RANDOM_SHUFFLE_COUNT = 10


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_virtual_user(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def build_world(items, vectors, algorithm_config) -> list[Island]:
    islands: list[Island] = []
    for key, entry in items:
        assign_scrap(islands, vectors[key], entry["text"], algorithm_config)
    return islands


def topic_purity_weighted(islands: list[Island], text_to_topic: dict[str, str]) -> tuple[float, int, int]:
    """Topic Purity = 각 Topic의 (다수결 실제 주제 스크랩 수) 합 / 전체 스크랩 수.
    1.0이면 모든 Topic이 완벽히 순수, 낮을수록 오염이 심하다.
    """
    total_scraps = 0
    pure_scraps = 0
    n_topics = 0
    max_contaminated_size = 0
    for isl in islands:
        for topic in isl.topics:
            n_topics += 1
            composition = Counter(text_to_topic[text] for text in topic.scraps)
            _, majority_count = composition.most_common(1)[0]
            total_scraps += len(topic.scraps)
            pure_scraps += majority_count
            if len(composition) > 1:
                max_contaminated_size = max(max_contaminated_size, len(topic.scraps))
    purity = pure_scraps / total_scraps if total_scraps else float("nan")
    return purity, n_topics, max_contaminated_size


def main() -> None:
    load_dotenv()
    config = load_config()
    embedding_provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])

    user = load_virtual_user("../experiments/virtual_users/ai_researcher.json")
    scraps = sorted(user["scraps"], key=lambda s: s["day"])
    base_items = [(s["text"], s) for s in scraps]
    text_to_topic = {s["text"]: s["topic"] for s in scraps}
    vectors = {s["text"]: embedding_provider.embed(s["text"]) for s in scraps}

    orderings: dict[str, list] = {"원래 Day 순서": base_items}
    for seed in range(1, RANDOM_SHUFFLE_COUNT + 1):
        orderings[f"Shuffle(seed={seed})"] = random.Random(seed).sample(base_items, len(base_items))

    table = Table(title="Experiment #27: Topic-level Order Sensitivity (AI Researcher)")
    for col in ("Order", "Topic 수", "Topic Purity", "최대 오염 Topic 크기"):
        table.add_column(col)

    purities = []
    for name, items in orderings.items():
        islands = build_world(items, vectors, config["algorithm"])
        purity, n_topics, max_contaminated = topic_purity_weighted(islands, text_to_topic)
        purities.append(purity)
        table.add_row(name, str(n_topics), f"{purity:.3f}", str(max_contaminated))

    console.print(table)

    import statistics

    console.print(
        f"\n[bold]Topic Purity: mean={statistics.mean(purities):.3f}, "
        f"std={statistics.stdev(purities):.3f}, "
        f"range=[{min(purities):.3f}, {max(purities):.3f}][/bold]"
    )
    console.print(
        "[bold]std가 0에 가까우면 순서와 무관하게 항상 비슷한 오염이 생긴다는 뜻(오염이 "
        "구조적 필연), std가 크면 Island threshold처럼 순서 의존적이라는 뜻이다.[/bold]"
    )


if __name__ == "__main__":
    main()
