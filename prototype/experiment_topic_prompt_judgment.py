"""Experiment #50: Topic-level Prompt Judgment - Prompt Objective의 통제 실험.

Finding #013(Semantic Resolution Mismatch)의 가장 큰 대안 설명을 제거하기
위한 실험이다: Experiment #45의 프롬프트가 "같은 상위 분야라는 이유만으로
높은 점수를 주지 말 것"을 명시했으므로, LLM이 Mechanism 수준으로 판단한 게
LLM의 능력 한계가 아니라 **우리가 그렇게 물어봤기 때문**일 수 있다.

이 실험은 딱 하나만 바꾼다 - 프롬프트. Experiment #47과 완전히 같은 pair
(같은 36개 스크랩, 같은 Case A/B/C 분류)에 대해, 이번엔 정반대로 "구체적
기법이 달라도 같은 상위 주제면 높은 점수를 줘라"고 명시한 프롬프트로
다시 점수를 매긴다(`pairwise_judge.py`의 mode="topic").

핵심 지표는 AUC가 아니라 **Δ = score_topic - score_mechanism**이다 -
Case B(같은 Topic, 다른 mechanism)에서만 선택적으로 Δ가 크면 "질문을
바꾸니 원하는 신호가 나온다"는 뜻이고, 모든 Case에서 Δ가 고르게 크면
"프롬프트가 그냥 점수를 전반적으로 올린 것뿐"이라는 뜻이다.
"""

import itertools
import json

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from sklearn.metrics import roc_auc_score

from experiment_anchor_model import load_virtual_user
from experiment_pairwise_granularity import MECHANISM_LABELS, classify, curated_sample
from pairwise_judge import OpenAIPairwiseJudge

console = Console()

MECHANISM_CACHE_PATH = "pairwise_judgment_cache.json"
TOPIC_CACHE_PATH = "pairwise_judgment_topic_cache.json"


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_cache(path: str) -> dict[str, float]:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_cache(path: str, cache: dict[str, float]) -> None:
    with open(path, "w") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def pair_key(text_a: str, text_b: str) -> str:
    a, b = sorted((text_a, text_b))
    return f"{a}|||{b}"


def main() -> None:
    load_dotenv()
    config = load_config()
    judge = OpenAIPairwiseJudge(model=config["label"]["model"])

    user = load_virtual_user("../experiments/virtual_users/ai_researcher.json")
    all_scraps = [s for s in user["scraps"] if s["text"] in MECHANISM_LABELS]
    scraps = curated_sample(all_scraps, per_topic_cap=4)  # Experiment #47과 동일 표본(seed=7 기본값)
    console.print(f"[bold]표본 {len(scraps)}개(Experiment #47과 동일), 쌍 {len(scraps)*(len(scraps)-1)//2}개[/bold]")

    mechanism_cache = load_cache(MECHANISM_CACHE_PATH)
    topic_cache = load_cache(TOPIC_CACHE_PATH)

    records = []
    done = 0
    for a, b in itertools.combinations(scraps, 2):
        key = pair_key(a["text"], b["text"])
        mech_score = mechanism_cache.get(key)
        if mech_score is None:
            mech_score = judge.score(a["text"], b["text"], mode="mechanism")
            mechanism_cache[key] = mech_score
        if key not in topic_cache:
            topic_cache[key] = judge.score(a["text"], b["text"], mode="topic")
        topic_score = topic_cache[key]

        case = classify(a, b)
        records.append(
            {
                "case": case,
                "same_topic": 1 if a["topic"] == b["topic"] else 0,
                "mechanism_score": mech_score,
                "topic_score": topic_score,
                "delta": topic_score - mech_score,
            }
        )
        done += 1
        if done % 100 == 0:
            save_cache(TOPIC_CACHE_PATH, topic_cache)
            save_cache(MECHANISM_CACHE_PATH, mechanism_cache)

    save_cache(TOPIC_CACHE_PATH, topic_cache)
    save_cache(MECHANISM_CACHE_PATH, mechanism_cache)

    table = Table(title="Experiment #50: Mechanism Prompt vs Topic Prompt (Case별)")
    for col in ("Case", "n", "mean mechanism_score", "mean topic_score", "mean Δ(topic-mechanism)"):
        table.add_column(col)

    for case in ("A", "B", "C"):
        case_records = [r for r in records if r["case"] == case]
        if not case_records:
            continue
        mean_mech = sum(r["mechanism_score"] for r in case_records) / len(case_records)
        mean_topic = sum(r["topic_score"] for r in case_records) / len(case_records)
        mean_delta = sum(r["delta"] for r in case_records) / len(case_records)
        table.add_row(case, str(len(case_records)), f"{mean_mech:.3f}", f"{mean_topic:.3f}", f"{mean_delta:+.3f}")

    console.print(table)

    labels = [r["same_topic"] for r in records]
    mech_scores = [r["mechanism_score"] for r in records]
    topic_scores = [r["topic_score"] for r in records]
    console.print(
        f"\n[bold]전체 ROC-AUC(같은 Topic 여부 기준) - "
        f"mechanism prompt: {roc_auc_score(labels, mech_scores):.3f}, "
        f"topic prompt: {roc_auc_score(labels, topic_scores):.3f}[/bold]"
    )


if __name__ == "__main__":
    main()
