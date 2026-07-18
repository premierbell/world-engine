"""Experiment #31: Top-k Member Representation as the actual attach decision rule.

Research Question #2("Anchor는 무엇으로 표현되어야 하는가?", `docs/anchor_model.md`)
의 다음 단계. Experiment #30은 진단이었다 - 이미 centroid 기준으로 내려진 attach
결정을 사후에 top-k 평균으로 다시 채점했을 뿐, top-k 평균을 실제 attach
판단 기준으로 써서 다른 결정을 내려본 적은 없다.

world.py의 night_batch_anchor()에 추가한 member_topk 파라미터로 실제 attach
판단 기준을 centroid(identity_vector) → top-k 멤버 평균으로 바꿔서,
Experiment #28과 동일한 방법론(Day1→7→30 증분, 순서 독립성, threshold sweep,
Topic Purity/Duplication Rate)으로 다시 검증한다.

Hypothesis: Experiment #30에서 top-k 평균이 centroid보다 correctness와 더
강하게 상관됐다면, 이걸 실제 판단 기준으로 쓸 때 Research Insight #001에서
확인한 Precision-Fragmentation Trade-off(threshold를 올리면 Purity는
좋아지지만 Island 수도 함께 늘어나기만 함)가 완화되어야 한다 - 즉 같은
Island 수 대에서 더 높은 Purity를 내거나, 더 적은 Island 수로 같은 Purity를
낼 수 있어야 한다.
"""

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from experiment_anchor_model import island_purity_weighted, load_virtual_user, topic_duplication_rate
from world import Island, night_batch_anchor

console = Console()


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def run_incremental(
    scraps: list[dict], vectors: dict[str, list[float]], attach_threshold: float, member_topk: int | None
) -> list[Island]:
    islands: list[Island] = []
    for day in sorted({s["day"] for s in scraps}):
        day_texts = [s["text"] for s in scraps if s["day"] == day]
        islands = night_batch_anchor(
            islands, day_texts, vectors, attach_threshold=attach_threshold, member_topk=member_topk
        )
    return islands


def run_order_independence(user_name: str, scraps: list[dict], vectors: dict, attach_threshold: float, member_topk: int) -> None:
    import random

    text_to_topic = {s["text"]: s["topic"] for s in scraps}
    base_texts_by_day = {d: [s["text"] for s in scraps if s["day"] == d] for d in sorted({s["day"] for s in scraps})}

    table = Table(title=f"Experiment #31: Order Independence, member_topk={member_topk} ({user_name})")
    for col in ("Order", "Island 수", "중복률", "Purity"):
        table.add_column(col)

    def run_with_order(seed: int | None) -> list[Island]:
        islands: list[Island] = []
        for day, texts in base_texts_by_day.items():
            ordered = random.Random(seed).sample(texts, len(texts)) if seed is not None else texts
            islands = night_batch_anchor(
                islands, ordered, vectors, attach_threshold=attach_threshold, member_topk=member_topk
            )
        return islands

    for name, seed in (("원래 Day 순서", None), ("Shuffle(seed=1)", 1), ("Shuffle(seed=2)", 2)):
        islands = run_with_order(seed)
        rate, _, _ = topic_duplication_rate(islands, text_to_topic)
        purity = island_purity_weighted(islands, text_to_topic)
        table.add_row(name, str(len(islands)), f"{rate:.1%}", f"{purity:.3f}")

    console.print(table)
    console.print()


def run_comparison_sweep(user_name: str, scraps: list[dict], vectors: dict, thresholds: dict[str, list[float]]) -> None:
    text_to_topic = {s["text"]: s["topic"] for s in scraps}

    table = Table(title=f"Experiment #31: Centroid vs Top-k(k=3) Attach 기준 비교 ({user_name})")
    for col in ("표현 방식", "threshold", "Island 수", "중복률", "Purity"):
        table.add_column(col)

    for label, member_topk, threshold_list in (
        ("centroid (기존, Experiment #28)", None, thresholds["centroid"]),
        ("top-3 member average", 3, thresholds["topk"]),
    ):
        for t in threshold_list:
            islands = run_incremental(scraps, vectors, t, member_topk)
            rate, _, _ = topic_duplication_rate(islands, text_to_topic)
            purity = island_purity_weighted(islands, text_to_topic)
            table.add_row(label, f"{t:.2f}", str(len(islands)), f"{rate:.1%}", f"{purity:.3f}")

    console.print(table)
    console.print()


def main() -> None:
    load_dotenv()
    config = load_config()
    embedding_provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])

    # top-k 평균 유사도는 centroid 유사도보다 체계적으로 높게 나올 수 있어(여러 멤버 중
    # 최댓값에 가까운 값들의 평균) 같은 threshold 값이 같은 의미가 아닐 수 있다 -
    # 두 표현 각각에 대해 별도 범위로 스윕한다.
    thresholds = {"centroid": [0.15, 0.20, 0.25, 0.30, 0.35, 0.40], "topk": [0.25, 0.30, 0.35, 0.40, 0.45, 0.50]}

    for user_name, path in (
        ("Backend User", "../experiments/virtual_users/backend_developer.json"),
        ("AI Researcher", "../experiments/virtual_users/ai_researcher.json"),
    ):
        user = load_virtual_user(path)
        scraps = user["scraps"]
        vectors = {s["text"]: embedding_provider.embed(s["text"]) for s in scraps}

        run_order_independence(user_name, scraps, vectors, attach_threshold=0.35, member_topk=3)
        run_comparison_sweep(user_name, scraps, vectors, thresholds)


if __name__ == "__main__":
    main()
