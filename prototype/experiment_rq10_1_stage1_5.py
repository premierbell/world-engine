"""Experiment #59: RQ10-1 Round 1.5 - Does behavioral context break the ceiling?

Round 1(Experiment #56~58)에서 질문(prompt wording)과 얕은 personal_reason
둘 다 AUC 0.90~0.92 천장에서 안 움직였다(Finding P2-002) - 병목이
content-inferable하지 않은 진짜 behavioral context의 부재라는 가설이었다.

이번 실험은 round1.json에 새로 채워진 4개 필드(purpose/time_horizon/
trigger/importance) 중 pairwise 입력에 자연스럽게 들어가는 purpose/
time_horizon/trigger 세 개를 content_summary에 붙여서(Neutral 하나로,
Round 1에서 검증된 대표 objective) content-only 베이스라인과 비교한다.
importance는 계획대로 제외(개별 속성이라 pairwise 비교에 안 맞고, 실제
채워진 값도 대부분 "검색해서 바로 찾을 정도로 낮음"으로 균일해서
추가 정보가 거의 없음).

이 실험 이후에는 결과와 무관하게 Round 1/1.5를 닫고 V1 설계로 넘어간다
(사용자와 합의된 stopping rule).
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
CONTENT_ONLY_CACHE_PATH = "rq10_1_stage1_pilot_cache.json"
BEHAVIORAL_CACHE_PATH = "rq10_1_stage1_5_behavioral_cache.json"


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


def with_behavioral_context(scrap: dict) -> str:
    return (
        f"{scrap['content_summary']}\n"
        f"(저장 이유: {scrap['purpose']})\n"
        f"(다시 볼 시점: {scrap['time_horizon']})\n"
        f"(다시 찾는 상황: {scrap['trigger']})"
    )


def main() -> None:
    load_dotenv()
    config = load_config()
    judge = OpenAIPairwiseJudge(model=config["label"]["model"])

    with open(ROUND1_PATH) as f:
        round1 = json.load(f)

    scraps = {s["id"]: s for s in round1["scraps"] if s.get("content_summary") and s.get("trigger")}
    console.print(f"[bold]표본 {len(scraps)}개[/bold]")

    group_of: dict[str, set[str]] = {}
    for g in round1["groups"]:
        for member in g["member_ids"]:
            if member in scraps:
                group_of.setdefault(member, set()).add(g["name"])

    ids = sorted(scraps.keys())
    pairs = list(itertools.combinations(ids, 2))
    labels = [1 if group_of.get(a, set()) & group_of.get(b, set()) else 0 for a, b in pairs]
    console.print(f"pair 수: {len(pairs)} (same-group: {sum(labels)}, diff-group: {len(labels) - sum(labels)})\n")

    content_only_cache = load_cache(CONTENT_ONLY_CACHE_PATH)
    behavioral_cache = load_cache(BEHAVIORAL_CACHE_PATH)

    content_only_scores = []
    behavioral_scores = []
    done = 0
    for a_id, b_id in pairs:
        content_only_scores.append(content_only_cache[pair_key(a_id, b_id, "neutral")])

        key = pair_key(a_id, b_id, "neutral_behavioral")
        if key not in behavioral_cache:
            text_a = with_behavioral_context(scraps[a_id])
            text_b = with_behavioral_context(scraps[b_id])
            behavioral_cache[key] = judge.score(text_a, text_b, mode="neutral")
        behavioral_scores.append(behavioral_cache[key])

        done += 1
        if done % 50 == 0:
            save_cache(BEHAVIORAL_CACHE_PATH, behavioral_cache)
            console.print(f"  {done}/{len(pairs)} pairs done")
    save_cache(BEHAVIORAL_CACHE_PATH, behavioral_cache)

    table = Table(title="Experiment #59: Neutral, content-only vs content+behavioral context")
    table.add_column("Condition")
    table.add_column("ROC-AUC")
    table.add_column("mean same-group")
    table.add_column("mean diff-group")

    for name, scores in (("content only", content_only_scores), ("content + behavioral", behavioral_scores)):
        auc = roc_auc_score(labels, scores)
        same = [s for s, l in zip(scores, labels) if l == 1]
        diff = [s for s, l in zip(scores, labels) if l == 0]
        table.add_row(name, f"{auc:.3f}", f"{np.mean(same):.3f}", f"{np.mean(diff):.3f}")
    console.print(table)

    same_pairs = [(p, s, c) for p, s, c, l in zip(pairs, content_only_scores, behavioral_scores, labels) if l == 1]
    same_pairs.sort(key=lambda x: x[1])

    err_table = Table(title="Same-group pairs, worst content-only scores -> behavioral context 효과")
    err_table.add_column("Pair")
    err_table.add_column("content-only")
    err_table.add_column("content+behavioral")
    err_table.add_column("Δ")
    for (a_id, b_id), s_only, s_ctx in same_pairs[:10]:
        err_table.add_row(f"{a_id}-{b_id}", f"{s_only:.2f}", f"{s_ctx:.2f}", f"{s_ctx - s_only:+.2f}")
    console.print(err_table)

    diff_pairs = [(p, s, c) for p, s, c, l in zip(pairs, content_only_scores, behavioral_scores, labels) if l == 0]
    diff_pairs.sort(key=lambda x: -x[1])

    err_table2 = Table(title="Diff-group pairs, highest content-only scores -> behavioral context 효과")
    err_table2.add_column("Pair")
    err_table2.add_column("content-only")
    err_table2.add_column("content+behavioral")
    err_table2.add_column("Δ")
    for (a_id, b_id), s_only, s_ctx in diff_pairs[:10]:
        err_table2.add_row(f"{a_id}-{b_id}", f"{s_only:.2f}", f"{s_ctx:.2f}", f"{s_ctx - s_only:+.2f}")
    console.print(err_table2)


if __name__ == "__main__":
    main()
