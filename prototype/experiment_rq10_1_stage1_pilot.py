"""Experiment #56: RQ10-1 Stage 1 Pilot - Real Ground Truth, summary-only.

docs/research_phase_2_rq10-0.md RQ10-1 Stage 1 참고. Round1(N=25, 사용자
본인의 실제 스크랩+그룹화)을 처음으로 Measurement Families(Mechanism/
Topic/Neutral/Relation)로 평가한다.

이번 실험은 의도적으로 content_summary만 쓴다 - personal_reason(저장
이유)을 같이 넣으면 "공부용/공부용"처럼 Ground Truth(같은 그룹 여부)를
직접 노출하는 leakage가 생긴다("Topic 때문이 아니라 둘 다 공부용이니까
같은 그룹"이라고 답할 수 있음). personal_reason은 상위 objective만
추려서 별도 Step에서, 그리고 질문 자체를 "같은 그룹인가"가 아니라
"사용자가 함께 보관할 것 같은가"로 바꿔서 다룬다.

N=25(실제로는 content_summary가 없는 s8 제외 24개, 276쌍, positive
19쌍)로 표본이 매우 작다 - 이 실험은 Pilot이다. AUC confidence
interval이 넓을 수 있다는 걸 감안하고 읽는다.
"""

import itertools
import json

import numpy as np
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from sklearn.metrics import roc_auc_score

from pairwise_judge import OpenAIPairwiseJudge

console = Console()

ROUND1_PATH = "../experiments/real_user_organization/round1.json"
CACHE_PATH = "rq10_1_stage1_pilot_cache.json"
MODES = ["mechanism", "topic", "neutral", "relation"]


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_cache(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_cache(path: str, cache: dict) -> None:
    with open(path, "w") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def pair_key(id_a: str, id_b: str, mode: str) -> str:
    a, b = sorted((id_a, id_b))
    return f"{a}|||{b}|||{mode}"


def main() -> None:
    load_dotenv()
    config = load_config()
    judge = OpenAIPairwiseJudge(model=config["label"]["model"])

    with open(ROUND1_PATH) as f:
        round1 = json.load(f)

    scraps = {s["id"]: s for s in round1["scraps"] if s.get("content_summary")}
    excluded = [s["id"] for s in round1["scraps"] if not s.get("content_summary")]
    console.print(f"[bold]표본 {len(scraps)}개 (content_summary 없음 제외: {excluded})[/bold]")

    group_of: dict[str, set[str]] = {}
    for g in round1["groups"]:
        for member in g["member_ids"]:
            if member in scraps:
                group_of.setdefault(member, set()).add(g["name"])

    ids = sorted(scraps.keys())
    pairs = list(itertools.combinations(ids, 2))
    labels = [1 if group_of.get(a, set()) & group_of.get(b, set()) else 0 for a, b in pairs]
    console.print(f"pair 수: {len(pairs)} (same-group: {sum(labels)}, diff-group: {len(labels) - sum(labels)})\n")

    cache = load_cache(CACHE_PATH)
    results: dict[str, list[float]] = {mode: [] for mode in MODES}

    done = 0
    for a_id, b_id in pairs:
        text_a = scraps[a_id]["content_summary"]
        text_b = scraps[b_id]["content_summary"]
        for mode in MODES:
            key = pair_key(a_id, b_id, mode)
            if key not in cache:
                cache[key] = judge.score(text_a, text_b, mode=mode)
            results[mode].append(cache[key])
        done += 1
        if done % 50 == 0:
            save_cache(CACHE_PATH, cache)
            console.print(f"  {done}/{len(pairs)} pairs done")
    save_cache(CACHE_PATH, cache)

    table = Table(title="Experiment #56: RQ10-1 Stage 1 Pilot (summary-only, real Ground Truth, N=24)")
    table.add_column("Objective")
    table.add_column("ROC-AUC")
    table.add_column("mean same-group score")
    table.add_column("mean diff-group score")

    for mode in MODES:
        scores = results[mode]
        auc = roc_auc_score(labels, scores)
        same = [s for s, l in zip(scores, labels) if l == 1]
        diff = [s for s, l in zip(scores, labels) if l == 0]
        table.add_row(mode.capitalize(), f"{auc:.3f}", f"{np.mean(same):.3f}", f"{np.mean(diff):.3f}")

    console.print(table)
    console.print(
        "\n[dim]N=25(24 valid) Pilot - AUC confidence interval이 넓다. "
        "personal_reason은 이 실험에 포함하지 않음(ground truth leakage 방지).[/dim]"
    )


if __name__ == "__main__":
    main()
