"""Experiment #46: Pairwise LLM Judgment Error Analysis.

Experiment #45가 보여준 신호(ROC-AUC 0.820)가 "진짜 의미 이해"에서
왔는지, 아니면 "우연히 같은 단어가 등장해서"(lexical shortcut) 같은
얕은 이유에서 왔는지 구분하지 않으면 이 신호를 신뢰할 수 없다. 경계
사례(같은 Topic인데 0점 - False Negative 후보, 다른 Topic인데 상대적으로
높은 점수 - False Positive 후보)를 골라서, 이번엔 점수와 함께 LLM의
근거(rationale)도 같이 받아 사람이 직접 분류한다:

- Type A(Genuine Semantic): 표현이 달라도 개념을 이해해서 판단
- Type B(Lexical Shortcut): 표면적인 단어 일치/불일치에 의존
- Type C(우연/오류): 근거가 부실하거나 판단이 이상함

world.py나 Anchor Model은 전혀 안 건드린다 - 순수 정성 분석이다.
"""

import itertools
import json

import yaml
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.table import Table

from experiment_anchor_model import load_virtual_user
from experiment_pairwise_llm_judgment import N_SAMPLES, pair_key, stratified_sample

console = Console()

_RATIONALE_PROMPT = (
    "다음 두 스크랩 요약을 비교해서, 둘이 같은 구체적인 하위 주제/기술을 다루고 "
    "있는지 0.0~1.0 사이의 점수로 평가하고, 그 이유를 한 문장으로 설명하라. "
    "같은 상위 분야라는 이유만으로 높은 점수를 주면 안 된다.\n\n"
    "출력은 정확히 다음 형식으로만:\n"
    "SCORE: <숫자>\n"
    "REASON: <한 문장>\n\n"
    "스크랩 A: {a}\n스크랩 B: {b}"
)


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def explain(client: OpenAI, model: str, text_a: str, text_b: str) -> tuple[float, str]:
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[{"role": "user", "content": _RATIONALE_PROMPT.format(a=text_a, b=text_b)}],
    )
    raw = response.choices[0].message.content.strip()
    score, reason = 0.5, "(파싱 실패)"
    for line in raw.splitlines():
        if line.upper().startswith("SCORE:"):
            try:
                score = float(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.upper().startswith("REASON:"):
            reason = line.split(":", 1)[1].strip()
    return score, reason


def main() -> None:
    load_dotenv()
    config = load_config()
    client = OpenAI()
    model = config["label"]["model"]

    user = load_virtual_user("../experiments/virtual_users/ai_researcher.json")
    scraps = user["scraps"]
    sample = stratified_sample(scraps, N_SAMPLES)

    with open("pairwise_judgment_cache.json") as f:
        cache = json.load(f)

    same_low, diff_high = [], []
    for a, b in itertools.combinations(sample, 2):
        key = pair_key(a["text"], b["text"])
        score = cache.get(key)
        if score is None:
            continue
        same = a["topic"] == b["topic"]
        if same and score <= 0.1:
            same_low.append((a, b, score))
        elif not same and score >= 0.2:
            diff_high.append((a, b, score))

    console.print(f"[bold]경계 사례: 같은 Topic인데 낮은 점수 {len(same_low)}건, "
                  f"다른 Topic인데 상대적으로 높은 점수 {len(diff_high)}건[/bold]\n")

    for label, cases in (("같은 Topic, 낮은 점수 (False Negative 후보)", same_low),
                          ("다른 Topic, 상대적으로 높은 점수 (False Positive 후보)", diff_high)):
        table = Table(title=f"Experiment #46: {label}")
        for col in ("Topic A / B", "원래 점수", "재질의 점수", "스크랩 A", "스크랩 B", "LLM 근거"):
            table.add_column(col, overflow="fold")
        for a, b, orig_score in cases:
            score, reason = explain(client, model, a["text"], b["text"])
            table.add_row(
                f"{a['topic']} / {b['topic']}", f"{orig_score:.2f}", f"{score:.2f}",
                a["text"][:60] + "...", b["text"][:60] + "...", reason,
            )
        console.print(table)
        console.print()


if __name__ == "__main__":
    main()
