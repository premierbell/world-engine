"""Experiment #51: LLM-Reranked Attach, Topic Prompt로 재실행.

Experiment #48(Mechanism Prompt로 rerank)은 Purity를 극적으로 개선했지만
Duplication은 전혀 개선하지 못했다(Finding #013, Semantic Resolution
Mismatch). Experiment #50이 그 원인을 "LLM 능력 한계"가 아니라 "Prompt
Objective"로 좁혔다(같은 pair, Topic Prompt로만 바꿔도 ROC-AUC
0.730→0.944, Case B가 선택적으로 크게 개선). 이 실험은 그 결론이 실제
시스템 품질(Purity/Duplication/Island 수)에도 이어지는지 검증한다 -
Experiment #48과 완전히 같은 설계(cosine top-3 → LLM rerank)에서
`pairwise_judge.py`의 mode만 "mechanism" → "topic"으로 바꾼다.

아직 Finding으로 승격하지 않는다 - Experiment #50은 offline 신호
개선만 확인했을 뿐 system behavior 개선은 이 실험이 처음 확인한다.
"""

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from experiment_anchor_model import island_purity_weighted, load_virtual_user, topic_duplication_rate
from experiment_llm_rerank_attach import run_cosine_baseline, run_llm_rerank
from pairwise_judge import OpenAIPairwiseJudge

console = Console()

TOPIC_CACHE_PATH = "pairwise_judgment_topic_cache.json"


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_topic_cache() -> dict[str, float]:
    import json

    try:
        with open(TOPIC_CACHE_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_topic_cache(cache: dict[str, float]) -> None:
    import json

    with open(TOPIC_CACHE_PATH, "w") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def run_persona(
    user_name: str, path: str, embedding_provider: OpenAIEmbeddingProvider, judge: OpenAIPairwiseJudge, cache: dict[str, float]
) -> None:
    user = load_virtual_user(path)
    scraps = user["scraps"]
    vectors = {s["text"]: embedding_provider.embed(s["text"]) for s in scraps}
    text_to_topic = {s["text"]: s["topic"] for s in scraps}

    table = Table(title=f"Experiment #51: Cosine Attach vs LLM-Reranked Attach (Topic Prompt, {user_name})")
    for col in ("방식", "Island 수", "Duplication Rate", "Topic Purity"):
        table.add_column(col)

    baseline = run_cosine_baseline(scraps, vectors, attach_threshold=0.30)
    rate, _, _ = topic_duplication_rate(baseline, text_to_topic)
    purity = island_purity_weighted(baseline, text_to_topic)
    table.add_row("Control: Cosine Attach (Exp #28)", str(len(baseline)), f"{rate:.1%}", f"{purity:.3f}")

    # Topic Prompt의 점수 분포(Case A 0.875 / B 0.704 / C 0.262, Experiment #50)에 맞춰 threshold 범위를 조정
    for llm_threshold in (0.4, 0.5, 0.6):
        treatment = run_llm_rerank(
            scraps, vectors, attach_threshold=0.30, llm_threshold=llm_threshold, judge=judge, cache=cache,
            mode="topic", cache_path=TOPIC_CACHE_PATH,
        )
        rate, _, _ = topic_duplication_rate(treatment, text_to_topic)
        purity = island_purity_weighted(treatment, text_to_topic)
        table.add_row(f"Treatment: LLM Rerank Topic (llm_threshold={llm_threshold})", str(len(treatment)), f"{rate:.1%}", f"{purity:.3f}")

    console.print(table)
    console.print()


def main() -> None:
    load_dotenv()
    config = load_config()
    embedding_provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])
    judge = OpenAIPairwiseJudge(model=config["label"]["model"])
    cache = load_topic_cache()

    for user_name, path in (
        ("Backend User", "../experiments/virtual_users/backend_developer.json"),
        ("AI Researcher", "../experiments/virtual_users/ai_researcher.json"),
    ):
        run_persona(user_name, path, embedding_provider, judge, cache)

    save_topic_cache(cache)


if __name__ == "__main__":
    main()
