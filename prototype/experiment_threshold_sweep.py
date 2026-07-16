"""Step 4 설계: Island/Topic Threshold를 정하기 위한 sweep 실험.

목표: threshold 값 하나를 고르는 게 아니라, threshold를 바꿀 때마다 Precision/Recall/F1이
자동으로 계산되고 PR 커브까지 저장되는 실험 환경을 만든다. Title/Summary/Topic 세 티어를
각각 돌려서 Island와 Topic이 서로 다른 난이도의 분류 문제라는 것을 확인한다.
"""

import json
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from similarity import cosine_similarity

console = Console()

DATASETS = {
    "title": "../golden_dataset/threshold/title/dataset.json",
    "summary": "../golden_dataset/threshold/summary/dataset.json",
    "topic_focused": "../golden_dataset/threshold/topic/dataset.json",
}

# 0.10~0.30은 촘촘하게(0.02 단위), 0.30~0.60은 기존대로(0.05 단위) - Precision이 무너지는 지점을 찾기 위함
ISLAND_THRESHOLDS = [round(0.10 + 0.02 * i, 2) for i in range(11)] + [0.35, 0.40, 0.45, 0.50, 0.55, 0.60]
# 0.35~0.60을 최적점 후보 구간으로 보고 촘촘하게, 그 바깥은 참고용으로 넓게
TOPIC_THRESHOLDS = [0.35, 0.38, 0.40, 0.42, 0.45, 0.48, 0.50, 0.52, 0.55, 0.58, 0.60, 0.65, 0.70]

PLOT_DIR = Path("../experiments/plots")


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_dataset(path: str) -> dict[str, dict]:
    with open(path) as f:
        return json.load(f)


def precision_recall_f1(pairs: list[tuple[float, bool]], threshold: float) -> tuple[float, float, float]:
    tp = fp = fn = 0
    for sim, is_positive in pairs:
        predicted = sim >= threshold
        if predicted and is_positive:
            tp += 1
        elif predicted and not is_positive:
            fp += 1
        elif not predicted and is_positive:
            fn += 1
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else float("nan")
    return precision, recall, f1


def build_pairs(dataset: dict[str, dict], vectors: dict[str, list[float]]):
    island_pairs: list[tuple[float, bool]] = []
    topic_pairs: list[tuple[float, bool]] = []
    for a, b in combinations(dataset.keys(), 2):
        sim = cosine_similarity(vectors[a], vectors[b])
        same_island = dataset[a]["island"] == dataset[b]["island"]
        island_pairs.append((sim, same_island))
        if same_island:
            same_topic = dataset[a]["topic"] == dataset[b]["topic"]
            topic_pairs.append((sim, same_topic))
    return island_pairs, topic_pairs


def print_sweep(
    title: str, pairs: list[tuple[float, bool]], thresholds: list[float]
) -> list[tuple[float, float, float, float]]:
    table = Table(title=title)
    for col in ("Threshold", "Precision", "Recall", "F1"):
        table.add_column(col)
    rows: list[tuple[float, float, float, float]] = []
    for t in thresholds:
        p, r, f1 = precision_recall_f1(pairs, t)
        table.add_row(f"{t:.2f}", f"{p:.3f}", f"{r:.3f}", f"{f1:.3f}")
        rows.append((t, p, r, f1))
    console.print(table)
    return rows


def save_pr_curve(rows: list[tuple[float, float, float, float]], title: str, out_path: Path) -> None:
    thresholds = [t for t, p, r, _ in rows]
    precisions = [p for t, p, r, _ in rows]
    recalls = [r for t, p, r, _ in rows]

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(recalls, precisions, marker="o", linewidth=1)
    for t, p, r in zip(thresholds, precisions, recalls):
        if p == p and r == r:  # NaN 제외
            ax.annotate(f"{t:.2f}", (r, p), textcoords="offset points", xytext=(4, 4), fontsize=7)
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title(title)
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> None:
    load_dotenv()
    config = load_config()
    provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])

    for tier, path in DATASETS.items():
        dataset = load_dataset(path)
        vectors = {key: provider.embed(dataset[key]["text"]) for key in dataset}
        island_pairs, topic_pairs = build_pairs(dataset, vectors)

        island_rows = print_sweep(f"({tier}) Island Threshold Sweep", island_pairs, ISLAND_THRESHOLDS)
        topic_rows = print_sweep(f"({tier}) Topic Threshold Sweep (같은 Island 내부)", topic_pairs, TOPIC_THRESHOLDS)

        save_pr_curve(island_rows, f"Island PR Curve ({tier})", PLOT_DIR / f"island_pr_{tier}.png")
        save_pr_curve(topic_rows, f"Topic PR Curve ({tier})", PLOT_DIR / f"topic_pr_{tier}.png")

    console.print(f"\nPR curves saved to {PLOT_DIR.resolve()}")


if __name__ == "__main__":
    main()
