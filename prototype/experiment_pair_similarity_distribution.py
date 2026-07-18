"""Experiment #35: Candidate-pair Similarity Distribution - tau 후보 탐색.

Research Insight #005(Objective Improvement != Product Improvement) 이후,
Objective v0에 Duplication을 직접 반영하는 항(Fragmentation Penalty)을
추가하기 전에 그 항의 파라미터 tau(비슷하다고 판단할 유사도 문턱값)를
근거 없이 스윕하지 않는다 - 실제 candidate 쌍들의 유사도 분포를 먼저
관찰해서, "같은 실제 주제" 쌍과 "다른 실제 주제" 쌍이 어디서 겹치고
갈리는지부터 본다.

이 실험에서만(offline 파라미터 캘리브레이션 목적) ground truth를 사용한다
- island_threshold/topic_threshold를 Experiment #6/#7에서 golden dataset
F1로 캘리브레이션했던 것과 같은 성격이다. 실제 attach 판단 로직(world.py)은
여전히 ground truth에 접근하지 않는다.
"""

from collections import Counter

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from experiment_anchor_model import load_virtual_user
from experiment_batch_objective import candidate_centroid
from similarity import cosine_similarity
from world import Island, compute_assignment_matrix, night_batch_anchor

console = Console()


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def dominant_topic(texts: list[str], text_to_topic: dict[str, str]) -> str:
    return Counter(text_to_topic[t] for t in texts).most_common(1)[0][0]


def collect_pairs(
    scraps: list[dict], vectors: dict[str, list[float]], attach_threshold: float
) -> tuple[list[float], list[float]]:
    """배치별로 candidate 쌍의 유사도를 모아서 (같은 실제 주제 쌍, 다른 실제 주제 쌍)으로
    나눈다. Fragmentation penalty가 실제로 attach 판단 시점에 쓸 수 있는 정보(candidate
    centroid 벡터)만 쓴다 - 여기서 ground truth는 분포를 관찰하는 용도로만 쓴다."""
    text_to_topic = {s["text"]: s["topic"] for s in scraps}
    islands: list[Island] = []
    same_topic_sims: list[float] = []
    diff_topic_sims: list[float] = []

    for day in sorted({s["day"] for s in scraps}):
        day_texts = [s["text"] for s in scraps if s["day"] == day]
        if islands:
            candidates, _, _ = compute_assignment_matrix(islands, day_texts, vectors)
            centroids = [candidate_centroid(texts, vectors) for texts in candidates]
            topics = [dominant_topic(texts, text_to_topic) for texts in candidates]
            for i in range(len(candidates)):
                for j in range(i + 1, len(candidates)):
                    sim = cosine_similarity(centroids[i], centroids[j])
                    if topics[i] == topics[j]:
                        same_topic_sims.append(sim)
                    else:
                        diff_topic_sims.append(sim)
        islands = night_batch_anchor(islands, day_texts, vectors, attach_threshold=attach_threshold)

    return same_topic_sims, diff_topic_sims


def print_histogram(user_name: str, same_sims: list[float], diff_sims: list[float]) -> None:
    bins = [(-1.0, 0.0), (0.0, 0.1), (0.1, 0.2), (0.2, 0.3), (0.3, 0.4), (0.4, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 1.01)]

    table = Table(title=f"Experiment #35: Candidate Pair Similarity 분포 ({user_name})")
    table.add_column("구간")
    table.add_column("같은 실제 주제 쌍")
    table.add_column("다른 실제 주제 쌍")

    for lo, hi in bins:
        same_n = sum(1 for s in same_sims if lo <= s < hi)
        diff_n = sum(1 for s in diff_sims if lo <= s < hi)
        table.add_row(f"[{lo:.1f}, {hi:.1f})", str(same_n), str(diff_n))

    console.print(table)
    console.print(
        f"  같은 주제 쌍: n={len(same_sims)}, mean={sum(same_sims)/len(same_sims):.3f} "
        f"(min={min(same_sims):.3f}, max={max(same_sims):.3f})" if same_sims else "  같은 주제 쌍: 없음"
    )
    console.print(
        f"  다른 주제 쌍: n={len(diff_sims)}, mean={sum(diff_sims)/len(diff_sims):.3f} "
        f"(min={min(diff_sims):.3f}, max={max(diff_sims):.3f})" if diff_sims else "  다른 주제 쌍: 없음"
    )

    # 후보 tau: 다른 주제 쌍의 상위 5%/10% 지점 - "이 이상이면 다른 주제 치고는 이례적으로 비슷하다"
    if diff_sims:
        sorted_diff = sorted(diff_sims, reverse=True)
        p10 = sorted_diff[max(0, len(sorted_diff) // 10 - 1)]
        p05 = sorted_diff[max(0, len(sorted_diff) // 20 - 1)]
        console.print(f"  다른 주제 쌍의 상위 10%/5% 지점(tau 후보): {p10:.3f} / {p05:.3f}")
    console.print()


def main() -> None:
    load_dotenv()
    config = load_config()
    embedding_provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])

    for user_name, path in (
        ("Backend User", "../experiments/virtual_users/backend_developer.json"),
        ("AI Researcher", "../experiments/virtual_users/ai_researcher.json"),
    ):
        user = load_virtual_user(path)
        scraps = user["scraps"]
        vectors = {s["text"]: embedding_provider.embed(s["text"]) for s in scraps}

        same_sims, diff_sims = collect_pairs(scraps, vectors, attach_threshold=0.30)
        print_histogram(user_name, same_sims, diff_sims)


if __name__ == "__main__":
    main()
