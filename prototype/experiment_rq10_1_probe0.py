"""Experiment #54: RQ10-1 Probe 0 - Sanity Check, not the main RQ10-1 experiment.

Question this probe actually answers:
    Which semantic objective best reconstructs the existing Topic labels?

Not yet asking (this needs real user/behavioral data, which doesn't exist yet):
    Which semantic objective best reflects human mental organization?

Ground truth ("Topic" label)는 가상 유저 데이터셋을 만들 때 수작업으로 부여한
레이블이라, 실제 사용자의 관심사 조직 방식의 근사치일 뿐이다 - Phase 1
내내 쓴 것과 같은 proxy. 이 실험의 결론은 "이 데이터셋 안에서 어느
objective가 이겼다"를 넘어서면 안 된다.

새 LLM 호출 없음 - Mechanism/Topic/Neutral/Relation 네 캐시 전부
Experiment #47/#50/#53에서 이미 채워져 있다.
"""

import itertools
import json

import numpy as np
from rich.console import Console
from rich.table import Table
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

from experiment_anchor_model import load_virtual_user
from experiment_pairwise_granularity import MECHANISM_LABELS, curated_sample
from experiment_resolution_ontology import pair_key

console = Console()

CACHES = {
    "Mechanism": "pairwise_judgment_cache.json",
    "Topic": "pairwise_judgment_topic_cache.json",
    "Neutral": "pairwise_judgment_neutral_cache.json",
    "Relation": "pairwise_judgment_relation_cache.json",
}


def load_cache(path: str) -> dict[str, float]:
    with open(path) as f:
        return json.load(f)


def cohens_d(same: list[float], diff: list[float]) -> float:
    n1, n2 = len(same), len(diff)
    var1, var2 = np.var(same, ddof=1), np.var(diff, ddof=1)
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    return (np.mean(same) - np.mean(diff)) / pooled_std


def main() -> None:
    user = load_virtual_user("../experiments/virtual_users/ai_researcher.json")
    all_scraps = [s for s in user["scraps"] if s["text"] in MECHANISM_LABELS]
    scraps = curated_sample(all_scraps, per_topic_cap=4)
    console.print(f"[bold]표본 {len(scraps)}개 (Experiment #47/#50/#52/#53과 동일)[/bold]\n")

    pairs = list(itertools.combinations(scraps, 2))
    labels = [1 if a["topic"] == b["topic"] else 0 for a, b in pairs]
    console.print(f"pair 수: {len(pairs)} (same-topic: {sum(labels)}, diff-topic: {len(labels) - sum(labels)})\n")

    table = Table(title="RQ10-1 Probe 0: Which objective best reconstructs the existing Topic labels?")
    for col in ("Objective", "ROC-AUC", "Precision@0.5", "Recall@0.5", "F1@0.5", "Cohen's d"):
        table.add_column(col)

    for name, path in CACHES.items():
        cache = load_cache(path)
        scores = [cache[pair_key(a["text"], b["text"])] for a, b in pairs]

        auc = roc_auc_score(labels, scores)
        preds = [1 if s >= 0.5 else 0 for s in scores]
        prec = precision_score(labels, preds, zero_division=0)
        rec = recall_score(labels, preds, zero_division=0)
        f1 = f1_score(labels, preds, zero_division=0)

        same = [s for s, l in zip(scores, labels) if l == 1]
        diff = [s for s, l in zip(scores, labels) if l == 0]
        d = cohens_d(same, diff)

        table.add_row(name, f"{auc:.3f}", f"{prec:.3f}", f"{rec:.3f}", f"{f1:.3f}", f"{d:.3f}")

    console.print(table)
    console.print(
        "\n[dim]Within the current virtual dataset only. This should not yet be "
        "interpreted as evidence about real human semantic organization - the "
        "evaluation target is still the virtual dataset's manually assigned "
        "Topic labels.[/dim]"
    )


if __name__ == "__main__":
    main()
