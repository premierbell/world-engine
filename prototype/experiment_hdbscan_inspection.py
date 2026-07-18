"""Experiment #22: Offline HDBSCAN Structure Inspection.

Experiment #21에서 Night Batch v0(Merge-only)가 Backend User(5→1 Island, 중복률
89%→0%)에서는 극적으로 효과가 있었지만 AI Researcher(7→6 Island, 중복률 77.8%→
77.8%, 변화 없음)에서는 거의 효과가 없었다. 원인을 추측하지 않고 직접 확인한다 -
성능을 올리는 게 목표가 아니라 구조를 관찰하는 게 목표다. purity_threshold 등
파라미터는 건드리지 않는다 - 지금 바꾸면 "purity 때문인지 HDBSCAN 구조 때문인지"가
섞여버린다.

확인 항목 3가지:
1. HDBSCAN이 이 데이터셋에서 실제로 몇 개의 클러스터를 만들었는가, Noise는 얼마나
   나왔는가.
2. 각 클러스터에 어떤 실제 Topic들이 섞여 들어갔는가 - "AI Research가 원래
   하나의 의미 공간이 아니라 여러 개일 수도 있다"는 가설을 직접 확인한다.
3. Online-only로 만들어진 각 Island가 어떤 HDBSCAN 클러스터에 얼마나 순수하게
   속하는지(purity) - Merge 후보가 왜 생기거나 안 생겼는지 설명한다.
"""

import json
import sys
from collections import Counter, defaultdict

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


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_virtual_user(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def main() -> None:
    load_dotenv()
    config = load_config()
    embedding_provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])

    path = sys.argv[1] if len(sys.argv) > 1 else "../experiments/virtual_users/ai_researcher.json"
    user = load_virtual_user(path)
    console.print(f"[bold]{user['user']}[/bold]: {user['persona']}\n")

    scraps = sorted(user["scraps"], key=lambda s: s["day"])
    text_to_topic = {s["text"]: s["topic"] for s in scraps}
    vectors = {s["text"]: embedding_provider.embed(s["text"]) for s in scraps}

    # ---- 1+2. offline HDBSCAN을 전체 스크랩에 돌려 클러스터 구조를 그대로 관찰 ----
    # night_batch()와 동일한 기본 파라미터(min_cluster_size=3, min_samples=1) - 건드리지 않는다.
    all_texts = [s["text"] for s in scraps]
    matrix = normalize(np.array([vectors[t] for t in all_texts]))
    labels = HDBSCAN(min_cluster_size=3, min_samples=1, metric="euclidean", copy=True).fit_predict(matrix)
    label_of = dict(zip(all_texts, labels))

    cluster_topics: dict[int, Counter] = defaultdict(Counter)
    for text, label in label_of.items():
        cluster_topics[label][text_to_topic[text]] += 1

    n_clusters = len({label for label in labels if label != -1})
    n_noise = int((labels == -1).sum())
    console.print(f"[bold]HDBSCAN 결과: {n_clusters}개 클러스터, Noise {n_noise}개 (전체 {len(all_texts)}개 중)[/bold]\n")

    cluster_table = Table(title="Experiment #22-1: HDBSCAN 클러스터 구성")
    for col in ("Cluster", "포함된 실제 Topic (개수)", "총 개수"):
        cluster_table.add_column(col)
    for label in sorted(cluster_topics.keys(), key=lambda l: (l == -1, l)):
        topics = cluster_topics[label]
        name = "Noise(-1)" if label == -1 else f"#{label}"
        topics_str = ", ".join(f"{topic}({n})" for topic, n in topics.most_common())
        cluster_table.add_row(name, topics_str, str(sum(topics.values())))
    console.print(cluster_table)
    console.print()

    # ---- 3. Online-only Island들이 각각 어떤 클러스터에 얼마나 순수하게 속하는지 ----
    islands: list[Island] = []
    for s in scraps:
        assign_scrap(islands, vectors[s["text"]], s["text"], config["algorithm"])

    purity_table = Table(title="Experiment #22-2: Online Island별 HDBSCAN Purity")
    for col in ("Island", "포함된 실제 Topic", "다수결 HDBSCAN 클러스터", "Purity"):
        purity_table.add_column(col)
    for isl in islands:
        texts = [text for topic in isl.topics for text in topic.scraps]
        island_labels = [label_of[t] for t in texts]
        non_noise = [l for l in island_labels if l != -1]
        topics_in_island = sorted({text_to_topic[t] for t in texts})
        if not non_noise:
            purity_table.add_row(f"#{isl.id}", ", ".join(topics_in_island), "전부 Noise", "-")
            continue
        dominant, count = Counter(non_noise).most_common(1)[0]
        purity = count / len(texts)
        purity_table.add_row(f"#{isl.id}", ", ".join(topics_in_island), f"#{dominant}", f"{purity:.2f}")
    console.print(purity_table)


if __name__ == "__main__":
    main()
