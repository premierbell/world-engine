"""Experiment #12: Offline HDBSCAN vs Greedy Online.

Experiment #11에서 "순서 의존성은 특정 Greedy 구현이 아니라 Online Incremental
Clustering이라는 접근 자체의 성질일 가능성이 높다"는 결론을 냈다. 이 실험은 처음으로
비교 대상(offline 접근)을 붙여서 그 가설을 검증한다. HDBSCAN은 전체 데이터를 한 번에
보고 결정하므로 이론적으로는 입력 순서와 무관해야 한다(order sensitivity std = 0) -
이걸 가정이 아니라 실측으로 확인하는 것이 이 실험의 핵심이다.
"""

import json
import random
import statistics
import time
from collections import Counter
from itertools import combinations

import numpy as np
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from sklearn.cluster import HDBSCAN
from sklearn.preprocessing import normalize

from embedding_provider import OpenAIEmbeddingProvider
from world import Island, assign_scrap

console = Console()

GREEDY_ISLAND_THRESHOLD = 0.24  # Greedy baseline (Experiment #6/#7)
MIN_CLUSTER_SIZE_SWEEP = list(range(2, 16))
MIN_SAMPLES_SWEEP = [1, 2, 3]  # min_cluster_size만 올리면 밀도 조건도 같이 빡빡해져 전부 noise가 됨 - 분리해서 스윕
RANDOM_SHUFFLE_COUNT = 30


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_dataset(path: str) -> dict[str, dict]:
    with open(path) as f:
        return json.load(f)


def pairwise_f1(predicted_of: dict[str, int], text_to_true: dict[str, str]) -> tuple[float, float, float]:
    all_texts = list(predicted_of.keys())
    tp = fp = fn = 0
    for a, b in combinations(all_texts, 2):
        same_pred = predicted_of[a] == predicted_of[b]
        same_true = text_to_true[a] == text_to_true[b]
        if same_pred and same_true:
            tp += 1
        elif same_pred and not same_true:
            fp += 1
        elif not same_pred and same_true:
            fn += 1
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = 2 * precision * recall / (precision + recall) if (tp + fp) and (tp + fn) else float("nan")
    return precision, recall, f1


def run_hdbscan(
    items: list[tuple[str, dict]], vectors: dict[str, list[float]], min_cluster_size: int, min_samples: int
) -> dict[str, int]:
    keys = [key for key, _ in items]
    # 코사인 유사도 기준 비교와 맞추기 위해 정규화 후 euclidean 사용
    # (unit vector에서는 euclidean 거리 순위가 cosine 유사도 순위와 동일하다: ||a-b||^2 = 2 - 2*cos_sim)
    matrix = normalize(np.array([vectors[key] for key in keys]))
    labels = HDBSCAN(
        min_cluster_size=min_cluster_size, min_samples=min_samples, metric="euclidean", copy=True
    ).fit_predict(matrix)

    next_noise_id = (int(labels.max()) + 1) if len(labels) else 0
    # noise(-1)는 서로 다른 섬(각자 singleton)으로 취급 - 억지로 하나로 묶어서 F1을 왜곡하지 않는다
    key_to_text = {key: entry["text"] for key, entry in items}
    predicted_by_text: dict[str, int] = {}
    for key, label in zip(keys, labels):
        if label == -1:
            predicted_by_text[key_to_text[key]] = next_noise_id
            next_noise_id += 1
        else:
            predicted_by_text[key_to_text[key]] = int(label)
    return predicted_by_text


def run_greedy(
    items: list[tuple[str, dict]], vectors: dict[str, list[float]], algorithm_config: dict
) -> dict[str, int]:
    islands: list[Island] = []
    for key, entry in items:
        assign_scrap(islands, vectors[key], entry["text"], algorithm_config)
    predicted: dict[str, int] = {}
    for isl in islands:
        for topic in isl.topics:
            for text in topic.scraps:
                predicted[text] = isl.id
    return predicted


def build_orderings(base_items: list[tuple[str, dict]]) -> dict[str, list[tuple[str, dict]]]:
    orderings: dict[str, list[tuple[str, dict]]] = {
        "Backend->AI->Sports": [
            item for label in ["Backend", "AI", "Sports"] for item in base_items if item[1]["island"] == label
        ],
        "Sports->Backend->AI": [
            item for label in ["Sports", "Backend", "AI"] for item in base_items if item[1]["island"] == label
        ],
    }
    for seed in range(1, RANDOM_SHUFFLE_COUNT + 1):
        orderings[f"Shuffle(seed={seed})"] = random.Random(seed).sample(base_items, len(base_items))
    return orderings


def main() -> None:
    load_dotenv()
    config = load_config()
    provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])
    algorithm_config = dict(config["algorithm"], island_threshold=GREEDY_ISLAND_THRESHOLD)

    dataset = load_dataset("../golden_dataset/threshold/topic/dataset.json")
    base_items = list(dataset.items())
    vectors = {key: provider.embed(entry["text"]) for key, entry in base_items}
    text_to_island = {entry["text"]: entry["island"] for _, entry in base_items}

    # Step 1: min_cluster_size x min_samples sweep (원본 순서로 baseline 탐색)
    # min_cluster_size만 올리면 밀도 조건도 같이 빡빡해져 전부 noise가 되는 걸 확인했음 -
    # 두 파라미터를 분리해서 스윕해야 domain-level(3개) 구조를 찾을 수 있다.
    sweep_table = Table(title="Experiment #12a: HDBSCAN min_cluster_size x min_samples sweep")
    for col in ("min_cluster_size", "min_samples", "Islands", "F1"):
        sweep_table.add_column(col)

    best_config, best_f1 = None, -1.0
    for mcs in MIN_CLUSTER_SIZE_SWEEP:
        for ms in MIN_SAMPLES_SWEEP:
            predicted = run_hdbscan(base_items, vectors, mcs, ms)
            _, _, f1 = pairwise_f1(predicted, text_to_island)
            n_islands = len(set(predicted.values()))
            sweep_table.add_row(str(mcs), str(ms), str(n_islands), f"{f1:.3f}" if f1 == f1 else "nan")
            if f1 == f1 and f1 > best_f1:
                best_f1, best_config = f1, (mcs, ms)

    console.print(sweep_table)
    best_mcs, best_ms = best_config
    console.print(
        f"[bold]Baseline candidate: min_cluster_size={best_mcs}, min_samples={best_ms} (F1={best_f1:.3f})[/bold]\n"
    )

    # Step 2: 같은 32가지 순서(Experiment #11과 동일)로 Greedy vs HDBSCAN 재실행
    orderings = build_orderings(base_items)

    order_table = Table(
        title=f"Experiment #12b: Order Sensitivity (Greedy vs HDBSCAN, min_cluster_size={best_mcs}, min_samples={best_ms})"
    )
    for col in ("Order", "Greedy Islands", "Greedy F1", "HDBSCAN Islands", "HDBSCAN F1"):
        order_table.add_column(col)

    greedy_f1s, greedy_islands, greedy_times = [], [], []
    hdbscan_f1s, hdbscan_islands, hdbscan_times = [], [], []

    for name, items in orderings.items():
        start = time.perf_counter()
        g_predicted = run_greedy(items, vectors, algorithm_config)
        greedy_times.append(time.perf_counter() - start)
        _, _, g_f1 = pairwise_f1(g_predicted, text_to_island)
        g_islands = len(set(g_predicted.values()))
        greedy_f1s.append(g_f1)
        greedy_islands.append(g_islands)

        start = time.perf_counter()
        h_predicted = run_hdbscan(items, vectors, best_mcs, best_ms)
        hdbscan_times.append(time.perf_counter() - start)
        _, _, h_f1 = pairwise_f1(h_predicted, text_to_island)
        h_islands = len(set(h_predicted.values()))
        hdbscan_f1s.append(h_f1)
        hdbscan_islands.append(h_islands)

        order_table.add_row(name, str(g_islands), f"{g_f1:.3f}", str(h_islands), f"{h_f1:.3f}")

    console.print(order_table)

    def summarize(f1s: list[float], islands: list[int], times: list[float]) -> tuple[str, str, str, str]:
        mode = Counter(islands).most_common(1)[0]
        return (
            f"{statistics.mean(f1s):.3f}",
            f"{statistics.stdev(f1s):.4f}",
            f"{mode[0]} ({mode[1]}/{len(islands)}) / {min(islands)}-{max(islands)}",
            f"{statistics.mean(times) * 1000:.2f}",
        )

    summary_table = Table(title="Experiment #12: Final Comparison (Greedy vs HDBSCAN)")
    for col in ("Algorithm", "F1 mean", "F1 std (order sensitivity)", "Islands (mode/range)", "Avg runtime (ms)"):
        summary_table.add_column(col)

    summary_table.add_row("Greedy (assign_scrap)", *summarize(greedy_f1s, greedy_islands, greedy_times))
    summary_table.add_row(
        f"HDBSCAN (mcs={best_mcs}, ms={best_ms})", *summarize(hdbscan_f1s, hdbscan_islands, hdbscan_times)
    )

    console.print(summary_table)


if __name__ == "__main__":
    main()
