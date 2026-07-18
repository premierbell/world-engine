"""Experiment #29: Margin Distribution Analysis (진단 전용, 아직 규칙 아님).

Research Insight #001(attach_threshold는 Precision-Fragmentation Trade-off만
조절한다) 이후, "attach 메커니즘을 어떻게 바꿀 것인가"를 바로 구현하지 않고
먼저 관찰한다 - 이 프로젝트의 반복된 패턴(Finding #001/#004/#006 전부 "처음
생각한 원인"보다 한 단계 아래에 진짜 원인이 있었다)을 따른다.

가설(Margin Hypothesis): 지금 night_batch_anchor()는 1등 Anchor가
attach_threshold만 넘으면 무조건 붙인다 - 2등 Anchor와의 격차(margin)를 안
본다. "애매한 attach"(margin이 작을 때)가 오염(서로 다른 실제 주제를 한
Anchor에 섞는 것)의 원인이라면, margin이 작을수록 잘못된 attach 비율이
높아야 한다.

world.py에 추가한 AttachTrace(best_similarity/second_similarity/margin)를
수집하고, 각 ATTACH 판단이 "옳았는지"(cluster의 다수결 실제 주제 ==
attach 직전 Anchor의 다수결 실제 주제)를 ground truth로 사후 채점해서
margin과의 상관관계를 확인한다. 아직 규칙(margin threshold)을 만들지
않는다 - 상관관계가 실제로 있는지부터 본다.
"""

import json
from collections import Counter

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from world import AttachTrace, Island, night_batch_anchor

console = Console()


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_virtual_user(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def run_incremental_with_trace(
    scraps: list[dict], vectors: dict[str, list[float]], attach_threshold: float
) -> tuple[list[Island], list[AttachTrace]]:
    islands: list[Island] = []
    trace: list[AttachTrace] = []
    for day in sorted({s["day"] for s in scraps}):
        day_texts = [s["text"] for s in scraps if s["day"] == day]
        islands = night_batch_anchor(islands, day_texts, vectors, attach_threshold=attach_threshold, trace=trace)
    return islands, trace


def dominant_topic(texts: list[str], text_to_topic: dict[str, str]) -> str:
    return Counter(text_to_topic[t] for t in texts).most_common(1)[0][0]


def score_attach_events(trace: list[AttachTrace], text_to_topic: dict[str, str]) -> list[dict]:
    """ATTACH 이벤트만 골라서 margin과 correctness(정답 여부)를 계산한다.
    correctness는 world.py가 아니라 여기(실험 스크립트, ground truth 접근 가능한 곳)에서만 판정한다.
    """
    scored = []
    for event in trace:
        if event.decision != "ATTACH":
            continue
        cluster_topic = dominant_topic(event.texts, text_to_topic)
        anchor_topic_before = dominant_topic(event.anchor_scraps_before, text_to_topic)
        scored.append(
            {
                "size": len(event.texts),
                "best_similarity": event.best_similarity,
                "second_similarity": event.second_similarity,
                "margin": event.margin,
                "correct": cluster_topic == anchor_topic_before,
                "cluster_topic": cluster_topic,
                "anchor_topic_before": anchor_topic_before,
            }
        )
    return scored


def print_margin_bucket_table(user_name: str, scored: list[dict]) -> None:
    with_margin = [s for s in scored if s["margin"] is not None]
    no_margin = [s for s in scored if s["margin"] is None]

    buckets = [(0.00, 0.02), (0.02, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 1.01)]
    table = Table(title=f"Experiment #29: Margin Bucket별 Attach 정확도 ({user_name})")
    for col in ("Margin 구간", "이벤트 수", "정확한 Attach", "정확도"):
        table.add_column(col)

    for lo, hi in buckets:
        bucket = [s for s in with_margin if lo <= s["margin"] < hi]
        if not bucket:
            table.add_row(f"[{lo:.2f}, {hi:.2f})", "0", "-", "-")
            continue
        correct = sum(1 for s in bucket if s["correct"])
        table.add_row(f"[{lo:.2f}, {hi:.2f})", str(len(bucket)), f"{correct}/{len(bucket)}", f"{correct/len(bucket):.1%}")

    console.print(table)
    if no_margin:
        no_margin_correct = sum(1 for s in no_margin if s["correct"])
        console.print(
            f"[dim]margin 계산 불가(비교 대상 Anchor 1개뿐)인 이벤트 {len(no_margin)}건, "
            f"그중 정확한 attach {no_margin_correct}건 - 위 버킷에는 포함 안 함[/dim]"
        )
    console.print()


def point_biserial(xs: list[float], corrects: list[float]) -> float:
    n = len(xs)
    mean_x = sum(xs) / n
    mean_c = sum(corrects) / n
    cov = sum((x - mean_x) * (c - mean_c) for x, c in zip(xs, corrects))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_c = sum((c - mean_c) ** 2 for c in corrects)
    return cov / ((var_x * var_c) ** 0.5) if var_x > 0 and var_c > 0 else float("nan")


def print_correlation(user_name: str, scored: list[dict]) -> None:
    with_margin = [s for s in scored if s["margin"] is not None]
    corrects_all = [1.0 if s["correct"] else 0.0 for s in scored]
    best_sims_all = [s["best_similarity"] for s in scored]
    best_corr = point_biserial(best_sims_all, corrects_all)
    console.print(
        f"[bold]{user_name}: best_similarity vs correctness correlation = {best_corr:.3f} "
        f"(n={len(scored)}, 전체 정확도={sum(corrects_all)/len(corrects_all):.1%})[/bold]"
    )

    if len(with_margin) < 2:
        console.print(f"[dim]{user_name}: margin 있는 이벤트가 너무 적어 margin 상관계수 계산 생략[/dim]\n")
        return
    margins = [s["margin"] for s in with_margin]
    corrects = [1.0 if s["correct"] else 0.0 for s in with_margin]
    margin_corr = point_biserial(margins, corrects)
    console.print(
        f"[bold]{user_name}: margin vs correctness correlation = {margin_corr:.3f} (n={len(with_margin)})[/bold]"
    )


def print_wrong_attach_detail(user_name: str, scored: list[dict]) -> None:
    wrong = sorted((s for s in scored if not s["correct"]), key=lambda s: (s["margin"] is None, s["margin"]))
    if not wrong:
        console.print(f"[dim]{user_name}: 잘못된 attach 없음[/dim]\n")
        return

    table = Table(title=f"Experiment #29: 잘못된 Attach 상세 ({user_name})")
    for col in ("크기", "best_sim", "second_sim", "margin", "cluster 주제", "anchor 기존 주제"):
        table.add_column(col)
    for s in wrong:
        table.add_row(
            str(s["size"]),
            f"{s['best_similarity']:.3f}",
            f"{s['second_similarity']:.3f}" if s["second_similarity"] is not None else "-",
            f"{s['margin']:.3f}" if s["margin"] is not None else "-",
            s["cluster_topic"],
            s["anchor_topic_before"],
        )
    console.print(table)
    console.print()


def main() -> None:
    load_dotenv()
    config = load_config()
    embedding_provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])

    for user_name, path in (
        ("Backend User", "../experiments/virtual_users/backend_developer.json"),
        ("AI Researcher", "../experiments/virtual_users/ai_researcher.json"),
    ):
        user = load_virtual_user(path)
        scraps = user["scraps"]
        text_to_topic = {s["text"]: s["topic"] for s in scraps}
        vectors = {s["text"]: embedding_provider.embed(s["text"]) for s in scraps}

        _, trace = run_incremental_with_trace(scraps, vectors, attach_threshold=0.30)
        scored = score_attach_events(trace, text_to_topic)

        console.print(
            f"[bold]{user_name}: 총 ATTACH 이벤트 {len(scored)}건 "
            f"(threshold=0.30, Day1->7->30 incremental)[/bold]"
        )
        print_margin_bucket_table(user_name, scored)
        print_correlation(user_name, scored)
        print_wrong_attach_detail(user_name, scored)


if __name__ == "__main__":
    main()
