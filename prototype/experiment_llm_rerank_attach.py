"""Experiment #48: LLM-Reranked Attach - does the pairwise signal actually
improve system quality?

Finding #012(Pairwise LLM Judgment reflects a finer semantic unit than the
Topic label)까지는 전부 "신호가 좋은가"를 검증했다. 이 실험은 처음으로
"좋은 신호가 실제 시스템(Purity/Duplication)을 개선하는가"를 검증한다 -
지금까지의 연구 전체에서 가장 중요한 분기점이다.

**설계 원칙(비용 폭발 방지 + ai_rules.md Rule 1 유지)**: LLM을 검색기로
쓰지 않는다 - candidate와 confirmed Anchor 전체를 비교시키면 비용이
폭발한다. 대신 2단계 구조를 쓴다:

1. **Recall(기존 cosine)**: compute_assignment_matrix()로 top-3 Anchor
   후보를 뽑는다(embedding, 이미 신뢰됨 - Finding #008은 "identity 판별"
   에서 실패했지 "후보 좁히기"에서 실패한 게 아니다).
2. **Rerank(신규 LLM)**: 그 top-3만 Pairwise LLM Judgment로 재점수화해서
   최종 Attach 여부를 결정한다.

AI는 여전히 "이해"(pairwise score)만 제공하고, 최종 CREATE/ATTACH 결정은
threshold로 알고리즘이 내린다(Rule 1 유지). world.py는 건드리지 않는다 -
이 메커니즘은 아직 실험 단계다.

Control(기존 cosine attach, Experiment #28과 동일)과 Treatment(LLM
rerank)를 같은 방법론(Day1→7→30 증분, Topic Purity/Duplication Rate)으로
직접 비교한다.
"""

import itertools
import json

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from experiment_anchor_model import island_purity_weighted, load_virtual_user, topic_duplication_rate
from pairwise_judge import OpenAIPairwiseJudge
from world import Island, compute_assignment_matrix, night_batch_anchor

console = Console()

CACHE_PATH = "pairwise_judgment_cache.json"
TOP_K_CANDIDATES = 3


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_cache() -> dict[str, float]:
    try:
        with open(CACHE_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_cache(cache: dict[str, float]) -> None:
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def pair_key(text_a: str, text_b: str) -> str:
    a, b = sorted((text_a, text_b))
    return f"{a}|||{b}"


def cached_score(cache: dict[str, float], judge: OpenAIPairwiseJudge, text_a: str, text_b: str) -> float:
    key = pair_key(text_a, text_b)
    if key not in cache:
        cache[key] = judge.score(text_a, text_b)
    return cache[key]


def run_cosine_baseline(scraps: list[dict], vectors: dict[str, list[float]], attach_threshold: float) -> list[Island]:
    islands: list[Island] = []
    for day in sorted({s["day"] for s in scraps}):
        day_texts = [s["text"] for s in scraps if s["day"] == day]
        islands = night_batch_anchor(islands, day_texts, vectors, attach_threshold=attach_threshold)
    return islands


def run_llm_rerank(
    scraps: list[dict],
    vectors: dict[str, list[float]],
    attach_threshold: float,
    llm_threshold: float,
    judge: OpenAIPairwiseJudge,
    cache: dict[str, float],
) -> list[Island]:
    islands: list[Island] = []
    for day in sorted({s["day"] for s in scraps}):
        day_texts = [s["text"] for s in scraps if s["day"] == day]
        if not islands:
            # 비교 대상 Anchor가 아직 없는 첫 배치는 기존 cosine 로직 그대로(Day1 seeding)
            islands = night_batch_anchor(islands, day_texts, vectors, attach_threshold=attach_threshold)
            continue

        candidates, anchors, matrix = compute_assignment_matrix(islands, day_texts, vectors)
        next_id = max((isl.id for isl in islands), default=-1) + 1
        for texts, row in zip(candidates, matrix):
            candidate_text = texts[0]
            top_idx = sorted(range(len(row)), key=lambda i: -row[i])[:TOP_K_CANDIDATES]
            llm_scored = [
                (i, cached_score(cache, judge, candidate_text, anchors[i].topics[0].scraps[0])) for i in top_idx
            ]
            best_i, best_llm_score = max(llm_scored, key=lambda p: p[1])
            if best_llm_score >= llm_threshold:
                anchors[best_i].topics[0].scraps.extend(texts)
            else:
                centroid = vectors[texts[0]] if len(texts) == 1 else [
                    sum(vectors[t][d] for t in texts) / len(texts) for d in range(len(vectors[texts[0]]))
                ]
                new_island = Island(next_id, centroid, texts[0])
                new_island.topics[0].scraps = list(texts)
                islands.append(new_island)
                next_id += 1
        save_cache(cache)
    return islands


def run_persona(user_name: str, path: str, embedding_provider: OpenAIEmbeddingProvider, judge: OpenAIPairwiseJudge, cache: dict[str, float]) -> None:
    user = load_virtual_user(path)
    scraps = user["scraps"]
    vectors = {s["text"]: embedding_provider.embed(s["text"]) for s in scraps}
    text_to_topic = {s["text"]: s["topic"] for s in scraps}

    table = Table(title=f"Experiment #48: Cosine Attach vs LLM-Reranked Attach ({user_name})")
    for col in ("방식", "Island 수", "Duplication Rate", "Topic Purity"):
        table.add_column(col)

    baseline = run_cosine_baseline(scraps, vectors, attach_threshold=0.30)
    rate, _, _ = topic_duplication_rate(baseline, text_to_topic)
    purity = island_purity_weighted(baseline, text_to_topic)
    table.add_row("Control: Cosine Attach (Exp #28)", str(len(baseline)), f"{rate:.1%}", f"{purity:.3f}")

    for llm_threshold in (0.2, 0.3, 0.4):
        treatment = run_llm_rerank(scraps, vectors, attach_threshold=0.30, llm_threshold=llm_threshold, judge=judge, cache=cache)
        rate, _, _ = topic_duplication_rate(treatment, text_to_topic)
        purity = island_purity_weighted(treatment, text_to_topic)
        table.add_row(f"Treatment: LLM Rerank (llm_threshold={llm_threshold})", str(len(treatment)), f"{rate:.1%}", f"{purity:.3f}")

    console.print(table)
    console.print()


def main() -> None:
    load_dotenv()
    config = load_config()
    embedding_provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])
    judge = OpenAIPairwiseJudge(model=config["label"]["model"])
    cache = load_cache()

    for user_name, path in (
        ("Backend User", "../experiments/virtual_users/backend_developer.json"),
        ("AI Researcher", "../experiments/virtual_users/ai_researcher.json"),
    ):
        run_persona(user_name, path, embedding_provider, judge, cache)

    save_cache(cache)


if __name__ == "__main__":
    main()
