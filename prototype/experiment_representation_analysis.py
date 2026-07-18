"""Experiment #30: Anchor Representation Analysis.

Experiment #29(Margin 가설 기각)가 남긴 질문: "가까운 Anchor를 찾는 것" 자체가
나쁜 판단 기준이라면, 원인이 "무엇을 기준으로 가까움을 재는가"(margin,
best_similarity)가 아니라 "Anchor를 무엇으로 표현하는가"(identity_vector라는
단일 평균 벡터)에 있을 수 있다 — Research Question #2: "Anchor는 무엇으로
표현되어야 하는가?"

바로 "Anchor를 멤버 집합으로 표현"(B안)을 구현하지 않고, 먼저 관찰한다:
Anchor 내부에 실제로 여러 실제 주제가 섞여 있을 때, 그 identity_vector(단일
평균 벡터)가 개별 멤버들과 비교해서 얼마나 "의미를 잃고" 있는지 직접 잰다.

Experiment #29에서 기록한 AttachTrace(특히 ATTACH 이벤트의
anchor_scraps_before)를 재사용해서, 매 ATTACH 이벤트마다 새 클러스터의
centroid를 세 가지 방식으로 비교한다:
1. centroid_similarity — cosine(cluster_centroid, anchor.identity_vector) (기존 판단 기준, Experiment #29의 best_similarity와 동일)
2. nearest_member_similarity — cosine(cluster_centroid, 각 기존 멤버 벡터) 중 최댓값
3. topk_avg_similarity — 위 멤버 유사도 중 상위 3개(또는 멤버 수가 3 미만이면 전부) 평균

세 지표 각각이 Experiment #29에서 정의한 correctness(cluster 다수결 실제
주제 == attach 직전 Anchor 다수결 실제 주제)와 얼마나 상관관계가 있는지
비교한다. member 기반 지표가 centroid 기반보다 뚜렷이 더 잘 맞으면, "단일
평균 벡터가 정보를 잃고 있다"는 게 진단이 아니라 실측으로 확인되는 것이다.
"""

from collections import Counter

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from experiment_margin_analysis import load_virtual_user, run_incremental_with_trace
from similarity import cosine_similarity

console = Console()


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def dominant_topic(texts: list[str], text_to_topic: dict[str, str]) -> str:
    return Counter(text_to_topic[t] for t in texts).most_common(1)[0][0]


def analyze_representation(trace, vectors: dict[str, list[float]], text_to_topic: dict[str, str], k: int = 3) -> list[dict]:
    rows = []
    for event in trace:
        if event.decision != "ATTACH":
            continue
        cluster_vectors = [vectors[t] for t in event.texts]
        centroid = [sum(vals) / len(vals) for vals in zip(*cluster_vectors)]

        member_sims = sorted(
            (cosine_similarity(centroid, vectors[m]) for m in event.anchor_scraps_before), reverse=True
        )
        nearest_member_sim = member_sims[0]
        topk_avg_sim = sum(member_sims[:k]) / min(k, len(member_sims))

        cluster_topic = dominant_topic(event.texts, text_to_topic)
        anchor_topic_before = dominant_topic(event.anchor_scraps_before, text_to_topic)

        rows.append(
            {
                "size": len(event.texts),
                "centroid_sim": event.best_similarity,
                "nearest_member_sim": nearest_member_sim,
                "topk_avg_sim": topk_avg_sim,
                "correct": cluster_topic == anchor_topic_before,
                "cluster_topic": cluster_topic,
                "anchor_topic_before": anchor_topic_before,
            }
        )
    return rows


def point_biserial(xs: list[float], corrects: list[float]) -> float:
    n = len(xs)
    mean_x = sum(xs) / n
    mean_c = sum(corrects) / n
    cov = sum((x - mean_x) * (c - mean_c) for x, c in zip(xs, corrects))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_c = sum((c - mean_c) ** 2 for c in corrects)
    return cov / ((var_x * var_c) ** 0.5) if var_x > 0 and var_c > 0 else float("nan")


def print_detail_table(user_name: str, rows: list[dict]) -> None:
    table = Table(title=f"Experiment #30: Centroid vs Member 기반 유사도 ({user_name})")
    for col in ("크기", "centroid_sim", "nearest_member_sim", "topk_avg_sim", "정답?", "cluster/anchor 주제"):
        table.add_column(col)
    for r in sorted(rows, key=lambda r: r["centroid_sim"]):
        table.add_row(
            str(r["size"]),
            f"{r['centroid_sim']:.3f}",
            f"{r['nearest_member_sim']:.3f}",
            f"{r['topk_avg_sim']:.3f}",
            "O" if r["correct"] else "X",
            f"{r['cluster_topic']} / {r['anchor_topic_before']}",
        )
    console.print(table)


def print_correlations(user_name: str, rows: list[dict]) -> None:
    corrects = [1.0 if r["correct"] else 0.0 for r in rows]
    for key, label in (
        ("centroid_sim", "centroid_similarity (기존 기준)"),
        ("nearest_member_sim", "nearest_member_similarity"),
        ("topk_avg_sim", "top-3_avg_similarity"),
    ):
        xs = [r[key] for r in rows]
        corr = point_biserial(xs, corrects)
        console.print(f"  {label}: correlation = {corr:.3f}")
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
        rows = analyze_representation(trace, vectors, text_to_topic)

        console.print(f"[bold]{user_name} (n={len(rows)} ATTACH 이벤트)[/bold]")
        print_detail_table(user_name, rows)
        print_correlations(user_name, rows)


if __name__ == "__main__":
    main()
