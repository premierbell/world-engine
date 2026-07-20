"""Experiment #58: RQ10-1 Stage 2b - Does user context (personal_reason) help?

Stage 2a(Experiment #57)에서 Neutral/Relation/Retrieval 세 프롬프트가
전부 AUC 0.90~0.92에 몰려 있었다 - 질문(prompt)을 더 바꿔도 안 좋아진다는
뜻이다. 병목이 prompt가 아니라 input(LLM이 사용자의 저장 의도를 모른다는
것)이라는 가설로 이동한다.

Measurement Family(Semantic Relatedness)는 이미 충분히 검증됐다고 보고
Neutral 하나만 대표로 쓴다 - prompt는 더 안 건드리고 input만 바꾼다:
- Condition A: content_summary만 (Experiment #56과 동일 점수, 캐시 재사용)
- Condition B: content_summary + personal_reason(사용자가 저장할 당시
  남긴 이유를 "사용자가 저장한 이유: ..."로 붙여서 같이 준다)

ROC-AUC 자체보다 **어떤 pair가 오답에서 정답으로 바뀌는지**(error
analysis)를 더 비중있게 본다 - N=19 positive라 AUC는 거의 안 움직일 수
있지만, 오류 패턴은 바뀔 수 있다.
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
CONTEXT_CACHE_PATH = "rq10_1_stage2b_context_cache.json"


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


def with_context(scrap: dict) -> str:
    return f"{scrap['content_summary']}\n(사용자가 저장한 이유: {scrap['personal_reason']})"


def main() -> None:
    load_dotenv()
    config = load_config()
    judge = OpenAIPairwiseJudge(model=config["label"]["model"])

    with open(ROUND1_PATH) as f:
        round1 = json.load(f)

    scraps = {s["id"]: s for s in round1["scraps"] if s.get("content_summary")}
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

    content_only_cache = load_cache(CACHE_PATH)
    context_cache = load_cache(CONTEXT_CACHE_PATH)

    content_only_scores = []
    context_scores = []
    done = 0
    for a_id, b_id in pairs:
        key_a = pair_key(a_id, b_id, "neutral")
        content_only_scores.append(content_only_cache[key_a])

        key_b = pair_key(a_id, b_id, "neutral_context")
        if key_b not in context_cache:
            text_a = with_context(scraps[a_id])
            text_b = with_context(scraps[b_id])
            context_cache[key_b] = judge.score(text_a, text_b, mode="neutral")
        context_scores.append(context_cache[key_b])

        done += 1
        if done % 50 == 0:
            save_cache(CONTEXT_CACHE_PATH, context_cache)
            console.print(f"  {done}/{len(pairs)} pairs done")
    save_cache(CONTEXT_CACHE_PATH, context_cache)

    table = Table(title="Experiment #58: Neutral, content-only vs content+personal_reason")
    table.add_column("Condition")
    table.add_column("ROC-AUC")
    table.add_column("mean same-group")
    table.add_column("mean diff-group")

    for name, scores in (("content only", content_only_scores), ("content + reason", context_scores)):
        auc = roc_auc_score(labels, scores)
        same = [s for s, l in zip(scores, labels) if l == 1]
        diff = [s for s, l in zip(scores, labels) if l == 0]
        table.add_row(name, f"{auc:.3f}", f"{np.mean(same):.3f}", f"{np.mean(diff):.3f}")
    console.print(table)

    # Error analysis: same-group pairs with lowest content-only score (false-negative candidates)
    same_pairs = [(p, s, c) for p, s, c, l in zip(pairs, content_only_scores, context_scores, labels) if l == 1]
    same_pairs.sort(key=lambda x: x[1])

    err_table = Table(title="Same-group pairs, worst content-only scores → does context fix them?")
    err_table.add_column("Pair")
    err_table.add_column("content-only")
    err_table.add_column("content+reason")
    err_table.add_column("Δ")
    for (a_id, b_id), s_only, s_ctx in same_pairs[:8]:
        err_table.add_row(f"{a_id}-{b_id}", f"{s_only:.2f}", f"{s_ctx:.2f}", f"{s_ctx - s_only:+.2f}")
    console.print(err_table)

    # Error analysis: diff-group pairs with highest content-only score (false-positive candidates)
    diff_pairs = [(p, s, c) for p, s, c, l in zip(pairs, content_only_scores, context_scores, labels) if l == 0]
    diff_pairs.sort(key=lambda x: -x[1])

    err_table2 = Table(title="Diff-group pairs, highest content-only scores → does context fix them?")
    err_table2.add_column("Pair")
    err_table2.add_column("content-only")
    err_table2.add_column("content+reason")
    err_table2.add_column("Δ")
    for (a_id, b_id), s_only, s_ctx in diff_pairs[:8]:
        err_table2.add_row(f"{a_id}-{b_id}", f"{s_only:.2f}", f"{s_ctx:.2f}", f"{s_ctx - s_only:+.2f}")
    console.print(err_table2)


if __name__ == "__main__":
    main()
