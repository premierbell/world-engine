"""Experiment #36: Structural Co-candidacy Signal - top-k Anchor 후보 공유가
Pairwise Similarity보다 "같은 Topic"을 더 잘 근사하는가?

Research Question #4("Duplication은 어떤 신호로 근사할 수 있는가?",
Research Insight #006) 첫 실험. Experiment #35에서 두 candidate의 직접
embedding 유사도(pairwise cosine)는 "같은 실제 주제인가"를 거의 구분하지
못한다는 게 확인됐다. 이번엔 다른 종류의 신호를 시도한다 - 두 candidate가
직접 안 닮아도, **어떤 Anchor들을 후보로 바라보고 있는지**(Experiment
#32의 assignment matrix, 이미 계산되는 정보)가 겹친다면 구조적으로 같은
곳을 가리키고 있다는 신호일 수 있다는 아이디어.

두 가지 구조적 신호를 시도한다:
1. **top-k overlap**: 두 candidate의 상위 k개 Anchor 후보 집합이 얼마나
   겹치는가(Jaccard 유사도).
2. **score vector correlation**: 두 candidate의 (전체 Anchor에 대한) 점수
   벡터 자체가 서로 얼마나 닮았는가(cosine) - "같은 유사도 패턴을
   가진다"는 걸 이산적인 top-k보다 연속적으로 포착.

Experiment #35와 같은 방법론(같은 실제 주제 쌍 vs 다른 실제 주제 쌍의
분포 비교)으로 이 두 신호가 direct pairwise similarity보다 판별력이
있는지 확인한다. 이 실험에서만(offline 신호 캘리브레이션 목적) ground
truth를 사용한다.
"""

from collections import Counter

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from experiment_anchor_model import load_virtual_user
from similarity import cosine_similarity
from world import Island, compute_assignment_matrix, night_batch_anchor

console = Console()

TOP_K = 3


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def dominant_topic(texts: list[str], text_to_topic: dict[str, str]) -> str:
    return Counter(text_to_topic[t] for t in texts).most_common(1)[0][0]


def top_k_ids(row: list[float], anchors: list[Island], k: int) -> set[int]:
    ranked = sorted(range(len(row)), key=lambda i: -row[i])[:k]
    return {anchors[i].id for i in ranked}


def top_k_overlap(row_i: list[float], row_j: list[float], anchors: list[Island], k: int) -> float:
    set_i, set_j = top_k_ids(row_i, anchors, k), top_k_ids(row_j, anchors, k)
    if not set_i and not set_j:
        return 0.0
    return len(set_i & set_j) / len(set_i | set_j)


def collect_signals(
    scraps: list[dict], vectors: dict[str, list[float]], attach_threshold: float
) -> tuple[dict[str, list[float]], dict[str, list[float]]]:
    text_to_topic = {s["text"]: s["topic"] for s in scraps}
    islands: list[Island] = []
    same = {"direct_sim": [], "topk_overlap": [], "score_vec_corr": []}
    diff = {"direct_sim": [], "topk_overlap": [], "score_vec_corr": []}

    for day in sorted({s["day"] for s in scraps}):
        day_texts = [s["text"] for s in scraps if s["day"] == day]
        if islands:
            candidates, anchors, matrix = compute_assignment_matrix(islands, day_texts, vectors)
            if len(candidates) >= 2 and anchors:
                topics = [dominant_topic(texts, text_to_topic) for texts in candidates]
                centroids = []
                for texts in candidates:
                    vecs = [vectors[t] for t in texts]
                    centroids.append([sum(v[d] for v in vecs) / len(vecs) for d in range(len(vecs[0]))])

                for i in range(len(candidates)):
                    for j in range(i + 1, len(candidates)):
                        bucket = same if topics[i] == topics[j] else diff
                        bucket["direct_sim"].append(cosine_similarity(centroids[i], centroids[j]))
                        bucket["topk_overlap"].append(top_k_overlap(matrix[i], matrix[j], anchors, TOP_K))
                        bucket["score_vec_corr"].append(cosine_similarity(matrix[i], matrix[j]))
        islands = night_batch_anchor(islands, day_texts, vectors, attach_threshold=attach_threshold)

    return same, diff


def summarize(label: str, values: list[float]) -> str:
    if not values:
        return f"{label}: 없음"
    return f"{label}: n={len(values)}, mean={sum(values)/len(values):.3f} (min={min(values):.3f}, max={max(values):.3f})"


def print_comparison(user_name: str, same: dict[str, list[float]], diff: dict[str, list[float]]) -> None:
    table = Table(title=f"Experiment #36: 신호별 same/diff topic 분리도 ({user_name})")
    for col in ("신호", "같은 주제 mean", "다른 주제 mean", "차이(같은-다른)"):
        table.add_column(col)

    for key, label in (
        ("direct_sim", "Direct Pairwise Similarity (Exp #35 대조군)"),
        ("topk_overlap", f"Top-{TOP_K} Anchor Overlap"),
        ("score_vec_corr", "Score Vector Correlation"),
    ):
        s, d = same[key], diff[key]
        if not s or not d:
            continue
        s_mean, d_mean = sum(s) / len(s), sum(d) / len(d)
        table.add_row(label, f"{s_mean:.3f}", f"{d_mean:.3f}", f"{s_mean - d_mean:+.3f}")

    console.print(table)
    for key, label in (("topk_overlap", f"Top-{TOP_K} Overlap"), ("score_vec_corr", "Score Vector Corr")):
        console.print(f"  {summarize(f'{label} (같은 주제)', same[key])}")
        console.print(f"  {summarize(f'{label} (다른 주제)', diff[key])}")
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

        same, diff = collect_signals(scraps, vectors, attach_threshold=0.30)
        print_comparison(user_name, same, diff)


if __name__ == "__main__":
    main()
