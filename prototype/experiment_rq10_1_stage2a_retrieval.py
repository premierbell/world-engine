"""Experiment #57: RQ10-1 Stage 2a - Align the question with Ground Truth.

Stage 1 Pilot(Experiment #56)에서 실제 Ground Truth(사용자가 함께 보관한
그룹)가 "같은 주제"가 아니라 "같은 용도로 나중에 참고할 묶음(task
bundle)"이었다는 게 드러났다. Neutral/Relation이 Topic보다 나았던 것도
이 어긋남 때문일 수 있다는 게 가설이었다 - 이 실험은 질문 자체를 Ground
Truth와 정렬시킨 새 프롬프트(retrieval, `pairwise_judge.py`)를
Neutral/Relation과 나란히 비교한다. Mechanism은 Stage 1 Pilot에서 적용
범위 밖(narrow domain of applicability)임이 확인돼 제외한다.

변수를 하나만 바꾼다 - 여전히 content_summary만 쓰고 personal_reason은
넣지 않는다(Ground Truth leakage 방지, Experiment #56과 동일 원칙).
personal_reason은 이 결과를 본 뒤 별도 Step(2b)에서 다룬다.
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
MODES = ["neutral", "relation", "retrieval"]


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

    table = Table(title="Experiment #57: RQ10-1 Stage 2a (question realigned with Ground Truth)")
    table.add_column("Objective")
    table.add_column("ROC-AUC")
    table.add_column("mean same-group")
    table.add_column("mean diff-group")

    for mode in MODES:
        scores = results[mode]
        auc = roc_auc_score(labels, scores)
        same = [s for s, l in zip(scores, labels) if l == 1]
        diff = [s for s, l in zip(scores, labels) if l == 0]
        table.add_row(mode.capitalize(), f"{auc:.3f}", f"{np.mean(same):.3f}", f"{np.mean(diff):.3f}")

    console.print(table)
    console.print(
        "\n[dim]Neutral/Relation은 Experiment #56 캐시 재사용(같은 cache 파일, "
        "새 호출 없음) - retrieval만 신규.[/dim]"
    )


if __name__ == "__main__":
    main()
