"""Experiment #32: Assignment Matrix Analysis.

Research Insight #002 이후, Research Question #2를 "Attach는 무엇을
최적화해야 하는가?"로 확장했다. 그 전에 한 단계 더 앞선 질문이 있다 -
**"Attach 문제는 정말 전역 최적화(global assignment) 문제인가?"**

지금까지(Experiment #28~31)는 전부 "점수 함수(scoring function)"만
바꿔왔다 - centroid냐 top-k냐, threshold를 얼마로 하느냐. 전부 Greedy
구조(각 candidate를 독립적으로, 가장 점수 높은 Anchor에 배정) 위에서의
변형이었다. 목적함수가 단순 합(Σ score)이라면, Global Optimization을
해도 Greedy와 정확히 같은 답이 나온다 - Optimizer를 설계하는 것 자체가
무의미해진다. Global Optimization이 의미를 가지려면 최소한의 필요조건이
있다: **같은 배치 안에서 서로 다른 candidate가 같은 Anchor를 두고
경쟁하는 상황이 실제로 존재해야 한다.** 그런 경쟁이 전혀 없다면(모든
candidate가 서로 다른 Anchor를 원한다면) Greedy와 Global Assignment는
항상 같은 결과를 낸다.

이 실험은 Optimizer를 구현하기 전에, world.py에 새로 추가한
`compute_assignment_matrix()`(attach 결정을 전혀 내리지 않는 순수 관찰용
함수)로 (candidate x Anchor) 유사도 행렬을 직접 관찰한다:
- Top1-Top2 gap 분포 (Experiment #29의 margin과 같은 개념이지만 이번엔
  판단이 아니라 "행렬 자체가 얼마나 애매한 candidate로 가득한가"를 본다)
- Entropy (한 candidate의 점수가 여러 Anchor에 고르게 퍼져 있는지, 1등이
  압도적인지)
- **Anchor 경쟁(contention)**: 같은 배치 안에서 서로 다른 candidate가
  1등으로 같은 Anchor를 고르는 경우가 실제로 몇 번이나 있는지 - 이게
  0에 가까우면 Global Optimization을 구현할 이유가 없다.
"""

import statistics
from collections import Counter, defaultdict

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from experiment_anchor_model import load_virtual_user
from world import Island, compute_assignment_matrix, night_batch_anchor

console = Console()


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def entropy(scores: list[float]) -> float:
    """유사도를 0 이상으로 shift한 뒤 정규화해서 Shannon entropy를 계산한다.
    1등이 압도적이면 0에 가깝고, 모든 Anchor가 비슷하면 log(N)에 가깝다."""
    shifted = [s - min(scores) + 1e-6 for s in scores]
    total = sum(shifted)
    probs = [s / total for s in shifted]
    return -sum(p * (0 if p <= 0 else __import__("math").log(p)) for p in probs)


def analyze_batch(candidates: list[list[str]], anchors: list[Island], matrix: list[list[float]]) -> list[dict]:
    rows = []
    for texts, scores in zip(candidates, matrix):
        if not scores:
            rows.append({"size": len(texts), "top1_id": None, "gap": None, "entropy": None, "n_anchors": 0})
            continue
        ranked = sorted(zip((a.id for a in anchors), scores), key=lambda p: -p[1])
        top1_id, top1_score = ranked[0]
        gap = (top1_score - ranked[1][1]) if len(ranked) > 1 else None
        rows.append(
            {
                "size": len(texts),
                "top1_id": top1_id,
                "top1_score": top1_score,
                "gap": gap,
                "entropy": entropy(scores),
                "n_anchors": len(anchors),
            }
        )
    return rows


def run_incremental_with_matrices(
    scraps: list[dict], vectors: dict[str, list[float]], attach_threshold: float
) -> list[dict]:
    """Day1->7->30 증분 처리를 재현하면서, 각 배치(Day7/Day30 - 비교 대상
    Anchor가 있는 배치만 의미 있음)마다 assignment matrix를 기록한다."""
    islands: list[Island] = []
    batch_records = []
    for day in sorted({s["day"] for s in scraps}):
        day_texts = [s["text"] for s in scraps if s["day"] == day]
        if islands:  # 비교할 Anchor가 있는 배치만 분석 대상
            candidates, anchors, matrix = compute_assignment_matrix(islands, day_texts, vectors)
            batch_records.append({"day": day, "candidates": candidates, "anchors": anchors, "matrix": matrix})
        islands = night_batch_anchor(islands, day_texts, vectors, attach_threshold=attach_threshold)
    return batch_records


def print_gap_entropy_table(user_name: str, batch_records: list[dict]) -> None:
    all_rows = []
    for record in batch_records:
        all_rows.extend(analyze_batch(record["candidates"], record["anchors"], record["matrix"]))

    gaps = [r["gap"] for r in all_rows if r["gap"] is not None]
    entropies = [r["entropy"] for r in all_rows if r["entropy"] is not None]

    table = Table(title=f"Experiment #32: Assignment Matrix 요약 통계 ({user_name})")
    for col in ("지표", "n", "mean", "median", "min", "max"):
        table.add_column(col)
    for label, values in (("Top1-Top2 gap", gaps), ("Entropy", entropies)):
        if not values:
            continue
        table.add_row(
            label, str(len(values)), f"{statistics.mean(values):.3f}", f"{statistics.median(values):.3f}",
            f"{min(values):.3f}", f"{max(values):.3f}",
        )
    console.print(table)

    small_gap = sum(1 for g in gaps if g < 0.02)
    console.print(f"  gap < 0.02(사실상 동점)인 candidate: {small_gap}/{len(gaps)}건\n")


def print_contention_table(user_name: str, batch_records: list[dict]) -> None:
    table = Table(title=f"Experiment #32: Anchor 경쟁(Contention) ({user_name})")
    for col in ("Day", "candidate 수", "Anchor 수", "1등이 겹치는 Anchor 수", "가장 많이 겹친 candidate 수"):
        table.add_column(col)

    total_contended_candidates = 0
    total_candidates = 0
    for record in batch_records:
        rows = analyze_batch(record["candidates"], record["anchors"], record["matrix"])
        top1_counts = Counter(r["top1_id"] for r in rows if r["top1_id"] is not None)
        contended_anchors = {aid: n for aid, n in top1_counts.items() if n > 1}
        contended_candidates = sum(contended_anchors.values())
        max_contention = max(top1_counts.values()) if top1_counts else 0
        total_contended_candidates += contended_candidates
        total_candidates += len(rows)
        table.add_row(
            str(record["day"]), str(len(record["candidates"])), str(len(record["anchors"])),
            str(len(contended_anchors)), str(max_contention),
        )

    console.print(table)
    console.print(
        f"  [bold]1등 Anchor가 다른 candidate와 겹치는 경우: "
        f"{total_contended_candidates}/{total_candidates}건[/bold]\n"
    )


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

        batch_records = run_incremental_with_matrices(scraps, vectors, attach_threshold=0.30)
        print_gap_entropy_table(user_name, batch_records)
        print_contention_table(user_name, batch_records)


if __name__ == "__main__":
    main()
