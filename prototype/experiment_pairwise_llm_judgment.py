"""Experiment #45: Pairwise LLM Judgment - Signal Existence Test.

Research Question #8("Topic Identity는 pairwise semantic judgment로
복원 가능한가?") 첫 실험. Finding #008(embedding)/#009(freeform tag)/
#010(tag graph)이 실패한 신호들은 전부 "문서 하나에서 독립적으로 계산
가능한 property"였다. 이번엔 성격이 다르다 - 문서 A와 B를 동시에 보여주고
"같은 구체적 주제를 다루는가"를 LLM에게 직접 물어서 얻는 **관계
(relation) 신호**다.

이 실험은 "Pairwise를 Anchor Model에 넣으면 품질이 좋아지는가"를 묻지
않는다 - 그건 너무 큰 질문이고, Anchor/CREATE/ATTACH를 전혀 쓰지 않는다.
묻는 건 하나뿐이다: **LLM Pairwise Score가 실제로 같은 Topic과 다른
Topic을 갈라내는가?** Experiment #35(direct similarity)/#37(tag)/#40
(tag graph)과 같은 방법론(같은 Topic 쌍 vs 다른 Topic 쌍 분포 비교) +
ROC-AUC로 분리도를 정량화한다.
"""

import itertools
import json
import random

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from sklearn.metrics import roc_auc_score

from experiment_anchor_model import load_virtual_user
from pairwise_judge import OpenAIPairwiseJudge

console = Console()

N_SAMPLES = 20
CACHE_PATH = "pairwise_judgment_cache.json"


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def stratified_sample(scraps: list[dict], n: int, seed: int = 1) -> list[dict]:
    rng = random.Random(seed)
    by_topic: dict[str, list[dict]] = {}
    for s in scraps:
        by_topic.setdefault(s["topic"], []).append(s)
    topics = sorted(by_topic)
    per_topic = max(1, n // len(topics))

    picked: list[dict] = []
    for topic in topics:
        pool = by_topic[topic]
        picked.extend(rng.sample(pool, min(per_topic, len(pool))))

    rng.shuffle(picked)
    return picked[:n]


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


def main() -> None:
    load_dotenv()
    config = load_config()
    judge = OpenAIPairwiseJudge(model=config["label"]["model"])

    user = load_virtual_user("../experiments/virtual_users/ai_researcher.json")
    scraps = user["scraps"]
    sample = stratified_sample(scraps, N_SAMPLES)

    console.print(f"[bold]표본 {len(sample)}개, 쌍 {len(sample) * (len(sample) - 1) // 2}개[/bold]")

    cache = load_cache()
    same_scores, diff_scores = [], []
    labels, scores = [], []
    parse_failures = 0

    for a, b in itertools.combinations(sample, 2):
        key = pair_key(a["text"], b["text"])
        if key not in cache:
            cache[key] = judge.score(a["text"], b["text"])
        score = cache[key]
        same = a["topic"] == b["topic"]
        (same_scores if same else diff_scores).append(score)
        labels.append(1 if same else 0)
        scores.append(score)
        if score == 0.5:
            parse_failures += 1

    save_cache(cache)

    table = Table(title="Experiment #45: Pairwise LLM Judgment Score 분포 (AI Researcher, n=20 표본)")
    for col in ("그룹", "n", "mean", "min", "max"):
        table.add_column(col)
    table.add_row("같은 Topic", str(len(same_scores)), f"{sum(same_scores)/len(same_scores):.3f}",
                   f"{min(same_scores):.3f}", f"{max(same_scores):.3f}")
    table.add_row("다른 Topic", str(len(diff_scores)), f"{sum(diff_scores)/len(diff_scores):.3f}",
                   f"{min(diff_scores):.3f}", f"{max(diff_scores):.3f}")
    console.print(table)

    diff = sum(same_scores) / len(same_scores) - sum(diff_scores) / len(diff_scores)
    auc = roc_auc_score(labels, scores)
    console.print(
        f"\n[bold]차이(같은-다른): {diff:+.3f}   ROC-AUC: {auc:.3f}"
        f"   (0.5=구분 못함, 1.0=완벽 구분)[/bold]"
    )
    if parse_failures:
        console.print(f"[dim]점수 파싱 실패로 0.5 처리된 쌍: {parse_failures}건[/dim]")


if __name__ == "__main__":
    main()
