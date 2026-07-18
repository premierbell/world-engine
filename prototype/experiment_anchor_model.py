"""Experiment #28: Anchor Model v0 (night_batch_anchor) Validation.

Anchor Model 설계(docs/anchor_model.md) 이후 첫 구현인 night_batch_anchor()를
검증한다. 최초 구현은 체이닝 버그를 갖고 있었다 - find_best_anchor가 배치
처리 도중 계속 자라는 result를 비교 대상으로 삼아서, 같은 배치 안에서 방금
막 생긴 Anchor에 뒤이어 처리되는 클러스터가 달라붙는 구조였다(Finding #004의
허브 체이닝이 scrap 레벨이 아니라 HDBSCAN-cluster 레벨에서 재현된 것). 비교
대상을 배치 시작 시점의 고정 스냅샷(`original_anchors`)으로 제한해서 고친
뒤 이 스크립트로 재검증한다.

**중요한 방법론 수정**: 최초 시도에서는 콜드스타트(confirmed_islands=[])로
전체 71개 스크랩을 한 번에 처리하며 attach_threshold를 스윕했는데, 이건
의미가 없다 - confirmed_islands가 비어 있으면 original_anchors도 비어
있어서 attach 자체가 절대 발생하지 않고(항상 새 Island 생성), threshold가
무슨 값이든 결과가 똑같다. Virtual User 데이터셋은 day 1(5개)/7(20개)/
30(46개) 세 번의 도착 시점을 갖고 있으므로, 실제 운영 패턴(Day1 이후 Night
Batch → confirmed_islands 생성 → Day7 새 스크랩만 그 위에 Night Batch →
Day30 새 스크랩만 다시 그 위에 Night Batch)을 그대로 재현해야 attach_threshold가
실제로 작동하는 조건에서 스윕할 수 있다.

세 가지를 확인한다:
1. 순서 독립성 - 각 day 배치 내부 스크랩 순서를 섞어도 최종 Island 구성이
   동일하게 나오는가.
2. attach_threshold sweep(day7/day30 배치에 적용) - Backend User와
   AI Researcher에서 threshold에 따라 최종 Island 수/중복률이 어떻게
   변하는가.
3. 질적 검사 - AI Researcher에서 Island가 여러 개로 나뉠 때, 그게 의미
   있는 주제 분리인지 아니면 그냥 noise로 분류된 개별 스크랩이 떨어져
   나가는 것뿐인지.
"""

import json
import random
from collections import Counter, defaultdict

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from world import Island, night_batch_anchor

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


def island_purity_weighted(islands: list[Island], text_to_ground_truth: dict[str, str]) -> float:
    """Experiment #27과 동일한 정의(evaluation_metrics.md)를 Island 레벨에
    적용한다 - 이 스크립트에서는 Island당 Topic이 하나뿐이라 사실상 Island
    Purity와 같다. Duplication Rate(binary)와 달리 오염의 '정도'를 반영한다.
    """
    total_scraps = 0
    pure_scraps = 0
    for isl in islands:
        for topic in isl.topics:
            composition = Counter(text_to_ground_truth[text] for text in topic.scraps)
            _, majority_count = composition.most_common(1)[0]
            total_scraps += len(topic.scraps)
            pure_scraps += majority_count
    return pure_scraps / total_scraps if total_scraps else float("nan")


def run_incremental(
    scraps: list[dict],
    vectors: dict[str, list[float]],
    attach_threshold: float,
    day_order_seed: int | None = None,
    day_groups: list[list[int]] | None = None,
) -> list[Island]:
    """Day 1 -> 7 -> 30 순서로, 각 day 배치마다 night_batch_anchor를 실행해
    실제 운영 패턴(누적 Confirmed Anchor 위에 새 스크랩만 얹는 것)을 재현한다.
    day_order_seed가 주어지면 각 배치 *내부* 스크랩 순서만 섞는다(배치 경계
    자체는 절대 안 섞는다 - 그건 미래 데이터를 과거로 당겨오는 것과 같아서
    실험 설계상 의미가 없다). day_groups로 여러 day를 하나의 배치로 묶을 수
    있다(Day1 초기 Anchor가 너무 작다는 가설 검증용, 예: [[1, 7], [30]]).
    """
    islands: list[Island] = []
    groups = day_groups if day_groups is not None else [[d] for d in sorted({s["day"] for s in scraps})]
    for group in groups:
        batch_texts = [s["text"] for s in scraps if s["day"] in group]
        if day_order_seed is not None:
            batch_texts = random.Random(day_order_seed).sample(batch_texts, len(batch_texts))
        islands = night_batch_anchor(islands, batch_texts, vectors, attach_threshold=attach_threshold)
    return islands


def run_order_independence(user_name: str, scraps: list[dict], vectors: dict, attach_threshold: float) -> None:
    text_to_topic = {s["text"]: s["topic"] for s in scraps}

    table = Table(title=f"Experiment #28: Order Independence ({user_name}, threshold={attach_threshold})")
    for col in ("Order", "Island 수", "중복 주제/전체", "중복률"):
        table.add_column(col)

    results = {"원래 Day 순서": run_incremental(scraps, vectors, attach_threshold, day_order_seed=None)}
    for seed in (1, 2):
        results[f"Day 내부 Shuffle(seed={seed})"] = run_incremental(
            scraps, vectors, attach_threshold, day_order_seed=seed
        )

    island_counts, dup_rates = [], []
    for name, islands in results.items():
        rate, dup, total = topic_duplication_rate(islands, text_to_topic)
        island_counts.append(len(islands))
        dup_rates.append(rate)
        table.add_row(name, str(len(islands)), f"{dup}/{total}", f"{rate:.1%}")

    console.print(table)
    console.print(
        f"[bold]Island 수: {island_counts} (모두 같으면 순서 독립 확정)  "
        f"중복률: {[f'{r:.1%}' for r in dup_rates]}[/bold]\n"
    )


def run_threshold_sweep(user_name: str, scraps: list[dict], vectors: dict, thresholds: list[float]) -> None:
    text_to_topic = {s["text"]: s["topic"] for s in scraps}

    table = Table(title=f"Experiment #28: attach_threshold Sweep ({user_name}, Day1->7->30 incremental)")
    for col in ("threshold", "Island 수", "중복 주제/전체", "중복률", "Purity", "최대 Island 크기"):
        table.add_column(col)

    for t in thresholds:
        islands = run_incremental(scraps, vectors, t)
        rate, dup, total = topic_duplication_rate(islands, text_to_topic)
        purity = island_purity_weighted(islands, text_to_topic)
        max_size = max((len(isl.topics[0].scraps) for isl in islands), default=0)
        table.add_row(f"{t:.2f}", str(len(islands)), f"{dup}/{total}", f"{rate:.1%}", f"{purity:.3f}", str(max_size))

    console.print(table)
    console.print()


def run_day1_hypothesis(user_name: str, scraps: list[dict], vectors: dict, thresholds: list[float]) -> None:
    """가설: Day1(5개)이 너무 작아 HDBSCAN이 의미 있는 클러스터를 못 만들고,
    그 결과 빈약한 초기 Anchor가 만들어지며, 이후 배치가 거기 무분별하게
    달라붙는다. Day1을 Day7과 합쳐서 첫 배치([1,7], [30])로 처리했을 때
    기존 Day1/7/30 3배치와 Purity/Duplication이 달라지는지 비교한다.
    """
    text_to_topic = {s["text"]: s["topic"] for s in scraps}

    table = Table(title=f"Experiment #28: Day1 Hypothesis ({user_name}, Day1을 Day7과 합친 첫 배치)")
    for col in ("threshold", "배치 구성", "Island 수", "중복률", "Purity"):
        table.add_column(col)

    for t in thresholds:
        baseline = run_incremental(scraps, vectors, t, day_groups=[[1], [7], [30]])
        merged = run_incremental(scraps, vectors, t, day_groups=[[1, 7], [30]])
        for label, islands in (("Day1|Day7|Day30 (기존)", baseline), ("[Day1+Day7]|Day30 (병합)", merged)):
            rate, _, _ = topic_duplication_rate(islands, text_to_topic)
            purity = island_purity_weighted(islands, text_to_topic)
            table.add_row(f"{t:.2f}", label, str(len(islands)), f"{rate:.1%}", f"{purity:.3f}")

    console.print(table)
    console.print()


def inspect_composition(user_name: str, scraps: list[dict], vectors: dict, attach_threshold: float) -> None:
    text_to_topic = {s["text"]: s["topic"] for s in scraps}
    islands = run_incremental(scraps, vectors, attach_threshold)

    table = Table(title=f"Experiment #28: Island 구성 상세 ({user_name}, threshold={attach_threshold})")
    for col in ("Island ID", "크기", "실제 주제 구성 (다수결부터)"):
        table.add_column(col)

    islands_sorted = sorted(islands, key=lambda isl: -len(isl.topics[0].scraps))
    for isl in islands_sorted:
        scrap_texts = isl.topics[0].scraps
        composition = Counter(text_to_topic[t] for t in scrap_texts)
        composition_str = ", ".join(f"{topic}×{n}" for topic, n in composition.most_common())
        table.add_row(str(isl.id), str(len(scrap_texts)), composition_str)

    console.print(table)
    console.print()


def main() -> None:
    load_dotenv()
    config = load_config()
    embedding_provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])

    thresholds = [0.15, 0.20, 0.25, 0.28, 0.30, 0.32, 0.35, 0.38, 0.40]

    for user_name, path in (
        ("Backend User", "../experiments/virtual_users/backend_developer.json"),
        ("AI Researcher", "../experiments/virtual_users/ai_researcher.json"),
    ):
        user = load_virtual_user(path)
        scraps = user["scraps"]
        vectors = {s["text"]: embedding_provider.embed(s["text"]) for s in scraps}

        run_order_independence(user_name, scraps, vectors, attach_threshold=0.30)
        run_threshold_sweep(user_name, scraps, vectors, thresholds)
        run_day1_hypothesis(user_name, scraps, vectors, thresholds=[0.20, 0.25, 0.30, 0.35])

    ai_user = load_virtual_user("../experiments/virtual_users/ai_researcher.json")
    ai_vectors = {s["text"]: embedding_provider.embed(s["text"]) for s in ai_user["scraps"]}
    for t in (0.20, 0.25, 0.30, 0.35):
        inspect_composition("AI Researcher", ai_user["scraps"], ai_vectors, attach_threshold=t)


if __name__ == "__main__":
    main()
