"""Experiment #55: RQ10-0 Probe 0 Replication on Backend User.

Experiment #54(Probe 0)는 AI Researcher 데이터셋 하나에서만 나온 결과다 -
"Topic ≈ Neutral"이 이 도메인 고유 현상인지, 일반적인 현상인지 아직
모른다. 같은 평가 체계·같은 파이프라인으로 도메인만 바꿔서 재현한다
(replication study). Mechanism 축은 뺀다 - Backend에는 mechanism
sub-label 주석이 없고, 지금 확인하려는 건 Mechanism이 아니라 Topic≈
Neutral의 일반성이기 때문이다(Topic/Neutral/Relation 세 objective만).

세 가지가 궁금하다:
1. Topic ≈ Neutral이 Backend에서도 유지되는가?
2. Relation의 관대함이 도메인마다 다르게 나타나는가(Backend는 Topic
   간 거리가 원래 넓은 도메인 - Finding #014)?
3. (Mechanism 없이도) Topic/Neutral/Relation 세 objective 사이의
   순서가 유지되는가?
"""

import itertools
import json
import random

import numpy as np
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

from experiment_anchor_model import load_virtual_user
from experiment_resolution_ontology import pair_key
from pairwise_judge import OpenAIPairwiseJudge

console = Console()

CACHES = {
    "Topic": "pairwise_judgment_topic_cache.json",
    "Neutral": "pairwise_judgment_neutral_cache.json",
    "Relation": "pairwise_judgment_relation_cache.json",
}
MODE_OF = {"Topic": "topic", "Neutral": "neutral", "Relation": "relation"}


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


def simple_per_topic_sample(scraps: list[dict], per_topic_cap: int, seed: int = 7) -> list[dict]:
    """Experiment #47의 curated_sample과 달리 mechanism 주석이 필요 없는 단순
    버전 - topic별로 최대 per_topic_cap개까지 무작위로 뽑는다."""
    rng = random.Random(seed)
    by_topic: dict[str, list[dict]] = {}
    for s in scraps:
        by_topic.setdefault(s["topic"], []).append(s)

    selected: list[dict] = []
    for topic, group in by_topic.items():
        shuffled = list(group)
        rng.shuffle(shuffled)
        selected.extend(shuffled[:per_topic_cap])
    return selected


def cohens_d(same: list[float], diff: list[float]) -> float:
    n1, n2 = len(same), len(diff)
    var1, var2 = np.var(same, ddof=1), np.var(diff, ddof=1)
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    return (np.mean(same) - np.mean(diff)) / pooled_std


def score_all_pairs(pairs, judge: OpenAIPairwiseJudge, mode: str, cache: dict, cache_path: str) -> None:
    done = 0
    for a, b in pairs:
        key = pair_key(a["text"], b["text"])
        if key not in cache:
            cache[key] = judge.score(a["text"], b["text"], mode=mode)
        done += 1
        if done % 100 == 0:
            save_cache(cache_path, cache)
            console.print(f"  [{mode}] {done}/{len(pairs)}")
    save_cache(cache_path, cache)


def main() -> None:
    load_dotenv()
    config = load_config()
    judge = OpenAIPairwiseJudge(model=config["label"]["model"])

    user = load_virtual_user("../experiments/virtual_users/backend_developer.json")
    scraps = simple_per_topic_sample(user["scraps"], per_topic_cap=4)
    console.print(f"[bold]Backend User 표본 {len(scraps)}개[/bold]\n")

    pairs = list(itertools.combinations(scraps, 2))
    labels = [1 if a["topic"] == b["topic"] else 0 for a, b in pairs]
    console.print(f"pair 수: {len(pairs)} (same-topic: {sum(labels)}, diff-topic: {len(labels) - sum(labels)})\n")

    caches = {name: load_cache(path) for name, path in CACHES.items()}
    for name, cache in caches.items():
        console.print(f"[bold]{name} 프롬프트로 채점 중...[/bold]")
        score_all_pairs(pairs, judge, MODE_OF[name], cache, CACHES[name])

    table = Table(title="RQ10-0 Probe 0 Replication (Backend User): Topic reconstruction by objective")
    for col in ("Objective", "ROC-AUC", "Precision@0.5", "Recall@0.5", "F1@0.5", "Cohen's d"):
        table.add_column(col)

    for name, cache in caches.items():
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


if __name__ == "__main__":
    main()
