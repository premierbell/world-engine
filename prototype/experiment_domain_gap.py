"""Experiment #13: Backend-AI Continuum Test.

Finding #002(Backend/AI가 어떤 알고리즘으로도 안 갈라짐)의 원인을 찾기 전에,
더 근본적인 질문을 먼저 확인한다: "Backend와 AI는 embedding 공간에서 실제로
연속적인가, 아니면 이 데이터셋에 우연히 경계 사례가 섞여서 그렇게 보이는가?"

golden_dataset/threshold/topic/dataset.json을 확인해보니 Backend는 순수
인프라 토픽(Spring/JPA, Redis, Kafka)뿐이고 AI는 순수 LLM/RAG 토픽뿐이다 -
"Vector DB", "Spring AI" 같은 경계 사례가 하나도 없다. 그런데도 계속 뭉친다면,
문제는 경계 사례가 아니라 "순수한" 두 도메인 자체가 이미 가깝다는 뜻이다.

Experiment #2(카테고리 내부/카테고리 간 평균 유사도)와 같은 방법론을, 이번엔
Topic 단위(7개)로 더 세밀하게 적용해서 Backend-AI 간 거리가 Backend-Sports나
AI-Sports 간 거리와 비교해 실제로 얼마나 가까운지 측정한다.
"""

import json
from collections import defaultdict
from itertools import combinations

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from similarity import cosine_similarity

console = Console()


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_dataset(path: str) -> dict[str, dict]:
    with open(path) as f:
        return json.load(f)


def avg_similarity(vectors_a: list[list[float]], vectors_b: list[list[float]], same_group: bool) -> float:
    if same_group:
        pairs = list(combinations(range(len(vectors_a)), 2))
        sims = [cosine_similarity(vectors_a[i], vectors_a[j]) for i, j in pairs]
    else:
        sims = [cosine_similarity(a, b) for a in vectors_a for b in vectors_b]
    return sum(sims) / len(sims) if sims else float("nan")


def main() -> None:
    load_dotenv()
    config = load_config()
    provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])

    dataset = load_dataset("../golden_dataset/threshold/topic/dataset.json")
    items = list(dataset.items())
    vectors = {key: provider.embed(entry["text"]) for key, entry in items}

    # Topic 단위로 벡터 묶기
    topic_vectors: dict[str, list[list[float]]] = defaultdict(list)
    topic_island: dict[str, str] = {}
    for key, entry in items:
        topic_vectors[entry["topic"]].append(vectors[key])
        topic_island[entry["topic"]] = entry["island"]

    topics = sorted(topic_vectors.keys())

    # 1. Topic x Topic 유사도 매트릭스 (item-level pairwise 평균)
    matrix_table = Table(title="Experiment #13: Topic x Topic Average Pairwise Similarity")
    matrix_table.add_column("Topic (Island)")
    for t in topics:
        matrix_table.add_column(f"{t}\n({topic_island[t]})")

    sim_cache: dict[tuple[str, str], float] = {}
    for t1 in topics:
        row = [f"{t1} ({topic_island[t1]})"]
        for t2 in topics:
            key = tuple(sorted((t1, t2)))
            if key not in sim_cache:
                sim_cache[key] = avg_similarity(topic_vectors[t1], topic_vectors[t2], same_group=(t1 == t2))
            sim = sim_cache[key]
            row.append(f"[bold]{sim:.3f}[/bold]" if t1 == t2 else f"{sim:.3f}")
        matrix_table.add_row(*row)

    console.print(matrix_table)

    # 2. Island-pair 단위로 묶어서 요약 (Backend-AI vs Backend-Sports vs AI-Sports vs 내부)
    islands = sorted({v["island"] for _, v in items})
    summary_table = Table(title="Experiment #13: Island-pair Summary (전체 pairwise 평균)")
    for col in ("Pair", "Avg Similarity", "관계"):
        summary_table.add_column(col)

    all_vectors_by_island: dict[str, list[list[float]]] = defaultdict(list)
    for key, entry in items:
        all_vectors_by_island[entry["island"]].append(vectors[key])

    rows = []
    for i, isl_a in enumerate(islands):
        for isl_b in islands[i:]:
            same = isl_a == isl_b
            sim = avg_similarity(all_vectors_by_island[isl_a], all_vectors_by_island[isl_b], same_group=same)
            label = f"{isl_a} internal" if same else f"{isl_a} <-> {isl_b}"
            rows.append((label, sim, "내부" if same else "교차"))

    rows.sort(key=lambda r: -r[1])
    for label, sim, kind in rows:
        summary_table.add_row(label, f"{sim:.4f}", kind)

    console.print(summary_table)


if __name__ == "__main__":
    main()
