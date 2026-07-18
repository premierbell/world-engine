"""Experiment #49: Score Distribution Overlap Analysis (Case A/B/C).

Experiment #48이 왜 Duplication을 못 줄였는지 확인한다 - threshold
조정으로 해결 가능한 문제(Case B/C가 잘 분리돼 있음)인지, 아니면
Signal Separability 문제(Case B/C가 겹침)인지. 새 API 호출은 하지
않는다 - Experiment #47에서 이미 채점한 캐시(`pairwise_judgment_cache.json`)
를 그대로 재사용해서 Case A/B/C 각각의 전체 점수 분포(히스토그램)를
비교하고, 몇 가지 threshold 후보에서 Precision/Recall을 계산한다.
"""

import itertools
import json
from collections import Counter

from rich.console import Console
from rich.table import Table

from experiment_anchor_model import load_virtual_user
from experiment_pairwise_granularity import MECHANISM_LABELS, classify, curated_sample

console = Console()

CACHE_PATH = "pairwise_judgment_cache.json"
THRESHOLDS = [0.1, 0.2, 0.3, 0.4]


def pair_key(text_a: str, text_b: str) -> str:
    a, b = sorted((text_a, text_b))
    return f"{a}|||{b}"


def main() -> None:
    user = load_virtual_user("../experiments/virtual_users/ai_researcher.json")
    all_scraps = [s for s in user["scraps"] if s["text"] in MECHANISM_LABELS]
    scraps = curated_sample(all_scraps, per_topic_cap=4)

    with open(CACHE_PATH) as f:
        cache = json.load(f)

    buckets: dict[str, list[float]] = {"A": [], "B": [], "C": []}
    for a, b in itertools.combinations(scraps, 2):
        key = pair_key(a["text"], b["text"])
        if key in cache:
            buckets[classify(a, b)].append(cache[key])

    table = Table(title="Experiment #49: Case별 점수 분포 (히스토그램)")
    table.add_column("Case")
    table.add_column("n")
    table.add_column("분포(score: count)")
    for case in "ABC":
        counts = Counter(buckets[case])
        dist = ", ".join(f"{s}:{n}" for s, n in sorted(counts.items()))
        table.add_row(case, str(len(buckets[case])), dist)
    console.print(table)
    console.print()

    same_topic_scores = buckets["A"] + buckets["B"]
    diff_topic_scores = buckets["C"]

    table2 = Table(title="Experiment #49: Threshold별 Precision/Recall (같은 Topic 여부 기준)")
    for col in ("threshold", "Recall (A∪B 통과)", "Precision", "통과한 C(노이즈) 수"):
        table2.add_column(col)

    for t in THRESHOLDS:
        tp = sum(1 for s in same_topic_scores if s >= t)
        fp = sum(1 for s in diff_topic_scores if s >= t)
        recall = tp / len(same_topic_scores) if same_topic_scores else float("nan")
        precision = tp / (tp + fp) if (tp + fp) else float("nan")
        table2.add_row(f"{t:.1f}", f"{recall:.1%} ({tp}/{len(same_topic_scores)})",
                        f"{precision:.1%}" if tp + fp else "-", str(fp))

    console.print(table2)


if __name__ == "__main__":
    main()
