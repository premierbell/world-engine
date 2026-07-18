"""Experiment #33: Does a candidate objective function make Greedy and Global
Assignment diverge?

Research Question #3("Attach는 어떤 목적함수를 최적화해야 하는가?",
`docs/anchor_model.md`)의 첫 실험. Experiment #32는 "경쟁이 존재한다"까지만
증명했다 - 목적함수가 단순 Σ score라면 경쟁이 아무리 많아도 Global
Optimization은 Greedy와 똑같은 답을 낸다(합을 최대화하는 배정은 각자 가장
높은 점수를 고르는 것과 동일하기 때문). Global Optimization이 실제로
의미를 가지려면, "같은 Anchor에 서로 다른 여러 candidate를 몰아넣는 것"
자체에 비용이 있는 목적함수가 필요하다.

**이 실험의 목적은 품질 개선이 아니라, Greedy와 다른 결정을 실제로 내리는
상황이 존재하는지 확인하는 것이다** - Optimizer(Hungarian, ILP 등)는 아직
구현하지 않는다.

## 목적함수 후보 (확정 아님, 첫 시도)

candidate 목적함수는 ground truth(실제 주제 라벨)를 쓸 수 없다 - 프로덕션
알고리즘은 정답을 모른 채 결정해야 한다(ai_rules.md Rule 1). 대신 이미
갖고 있는 신호(similarity, candidate 벡터)만으로 "같은 Anchor에 서로 다른
candidate를 몰아넣는 위험"을 근사한다:

    J(assignment) = Σ_c attach_score(c, assignment[c])
                    - λ * Σ_{(c1,c2): 같은 Anchor로 배정, c1≠c2} (1 - cos_sim(c1, c2))

각 candidate가 Anchor에 붙을 때 얻는 점수(attach_score, "새 Anchor" 선택지는
attach_threshold를 기준값으로 취급)의 합에서, 같은 Anchor에 함께 배정된
candidate끼리 서로 안 닮았을수록(1 - cos_sim이 큼) 벌점을 뺀다. λ=0이면
그냥 Greedy와 동일한 목적함수다(대조군).

## 검증 방법

Optimizer를 만드는 대신, Greedy 배정에서 시작해 지역 탐색(local search:
각 candidate를 다른 Anchor/신규로 재배정했을 때 J가 좋아지면 채택, 안
좋아지면 유지)을 한 번 돌려서 "Greedy보다 J가 더 높은 배정이 존재하는가"만
확인한다. 존재한다면 Greedy ≠ Global Optimum이라는 존재증명(existence
proof)이 되고, 그 자체로 Experiment #33의 목표가 달성된다.
"""

from collections import defaultdict

import numpy as np
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from experiment_anchor_model import load_virtual_user
from similarity import cosine_similarity
from world import Island, compute_assignment_matrix, night_batch_anchor

console = Console()

NEW = -1  # "새 Anchor 생성"을 가리키는 가상의 배정 대상


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def candidate_centroid(texts: list[str], vectors: dict[str, list[float]]) -> list[float]:
    return vectors[texts[0]] if len(texts) == 1 else np.mean([vectors[t] for t in texts], axis=0).tolist()


def objective(
    assignment: list[int],
    candidates: list[list[str]],
    matrix: list[list[float]],
    centroids: list[list[float]],
    attach_threshold: float,
    lam: float,
) -> float:
    total = sum(
        matrix[i][a] if a != NEW else attach_threshold for i, a in enumerate(assignment)
    )
    groups: dict[int, list[int]] = defaultdict(list)
    for i, a in enumerate(assignment):
        if a != NEW:
            groups[a].append(i)
    penalty = 0.0
    for members in groups.values():
        for x in range(len(members)):
            for y in range(x + 1, len(members)):
                penalty += 1 - cosine_similarity(centroids[members[x]], centroids[members[y]])
    return total - lam * penalty


def greedy_assignment(matrix: list[list[float]], attach_threshold: float) -> list[int]:
    assignment = []
    for row in matrix:
        if not row:
            assignment.append(NEW)
            continue
        best_a = max(range(len(row)), key=lambda a: row[a])
        assignment.append(best_a if row[best_a] >= attach_threshold else NEW)
    return assignment


def local_search(
    assignment: list[int],
    candidates: list[list[str]],
    matrix: list[list[float]],
    centroids: list[list[float]],
    attach_threshold: float,
    lam: float,
    max_passes: int = 5,
) -> tuple[list[int], int]:
    assignment = list(assignment)
    n_anchors = len(matrix[0]) if matrix and matrix[0] else 0
    total_moves = 0
    for _ in range(max_passes):
        improved = False
        for i in range(len(candidates)):
            current = objective(assignment, candidates, matrix, centroids, attach_threshold, lam)
            best_alt, best_obj = assignment[i], current
            for alt in list(range(n_anchors)) + [NEW]:
                if alt == assignment[i]:
                    continue
                trial = list(assignment)
                trial[i] = alt
                trial_obj = objective(trial, candidates, matrix, centroids, attach_threshold, lam)
                if trial_obj > best_obj + 1e-9:
                    best_alt, best_obj = alt, trial_obj
            if best_alt != assignment[i]:
                assignment[i] = best_alt
                improved = True
                total_moves += 1
        if not improved:
            break
    return assignment, total_moves


def run_lambda_sweep(user_name: str, scraps: list[dict], vectors: dict, attach_threshold: float, lambdas: list[float]) -> None:
    islands: list[Island] = []
    all_candidates, all_anchors, all_matrix = [], [], []
    for day in sorted({s["day"] for s in scraps}):
        day_texts = [s["text"] for s in scraps if s["day"] == day]
        if islands:
            candidates, anchors, matrix = compute_assignment_matrix(islands, day_texts, vectors)
            if candidates:
                all_candidates.append(candidates)
                all_anchors.append(anchors)
                all_matrix.append(matrix)
        islands = night_batch_anchor(islands, day_texts, vectors, attach_threshold=attach_threshold)

    table = Table(title=f"Experiment #33: Lambda Sweep - Greedy vs Local Search ({user_name})")
    for col in ("lambda", "배치 수", "재배정된 candidate 수", "J(greedy)", "J(local search)", "ΔJ"):
        table.add_column(col)

    for lam in lambdas:
        total_moves = 0
        j_greedy_sum, j_ls_sum = 0.0, 0.0
        for candidates, matrix in zip(all_candidates, all_matrix):
            centroids = [candidate_centroid(texts, vectors) for texts in candidates]
            greedy = greedy_assignment(matrix, attach_threshold)
            improved, moves = local_search(greedy, candidates, matrix, centroids, attach_threshold, lam)
            total_moves += moves
            j_greedy_sum += objective(greedy, candidates, matrix, centroids, attach_threshold, lam)
            j_ls_sum += objective(improved, candidates, matrix, centroids, attach_threshold, lam)
        table.add_row(
            f"{lam:.2f}", str(len(all_candidates)), str(total_moves),
            f"{j_greedy_sum:.3f}", f"{j_ls_sum:.3f}", f"{j_ls_sum - j_greedy_sum:.3f}",
        )

    console.print(table)
    console.print()


def inspect_reassignments(user_name: str, scraps: list[dict], vectors: dict, attach_threshold: float, lam: float) -> None:
    """lambda가 재배정을 만드는 지점에서, 실제로 뭐가 뭐로 바뀌는지 눈으로 확인한다
    (참고용 - Purity/Duplication 개선을 주장하는 게 아니라 재배정이 '말이 되는지'만 본다)."""
    text_to_topic = {s["text"]: s["topic"] for s in scraps}
    islands: list[Island] = []
    table = Table(title=f"Experiment #33: 재배정 상세 (lambda={lam}, {user_name})")
    for col in ("Day", "candidate 주제", "Greedy 배정", "Local Search 배정", "Anchor 기존 주제"):
        table.add_column(col)

    any_row = False
    for day in sorted({s["day"] for s in scraps}):
        day_texts = [s["text"] for s in scraps if s["day"] == day]
        if islands:
            candidates, anchors, matrix = compute_assignment_matrix(islands, day_texts, vectors)
            if candidates:
                centroids = [candidate_centroid(texts, vectors) for texts in candidates]
                greedy = greedy_assignment(matrix, attach_threshold)
                improved, _ = local_search(greedy, candidates, matrix, centroids, attach_threshold, lam)
                for i, (g, ls) in enumerate(zip(greedy, improved)):
                    if g == ls:
                        continue
                    any_row = True
                    from collections import Counter

                    cluster_topic = Counter(text_to_topic[t] for t in candidates[i]).most_common(1)[0][0]
                    g_label = f"Anchor {anchors[g].id}" if g != NEW else "신규"
                    ls_label = f"Anchor {anchors[ls].id}" if ls != NEW else "신규"
                    anchor_for_display = g if g != NEW else ls
                    anchor_topic = (
                        Counter(text_to_topic[t] for t in anchors[anchor_for_display].topics[0].scraps).most_common(1)[0][0]
                        if anchor_for_display != NEW
                        else "-"
                    )
                    table.add_row(str(day), cluster_topic, g_label, ls_label, anchor_topic)
        islands = night_batch_anchor(islands, day_texts, vectors, attach_threshold=attach_threshold)

    if any_row:
        console.print(table)
    else:
        console.print(f"[dim]{user_name}, lambda={lam}: 재배정 없음[/dim]")
    console.print()


def main() -> None:
    load_dotenv()
    config = load_config()
    embedding_provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])

    lambdas = [0.0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.2]

    for user_name, path in (
        ("Backend User", "../experiments/virtual_users/backend_developer.json"),
        ("AI Researcher", "../experiments/virtual_users/ai_researcher.json"),
    ):
        user = load_virtual_user(path)
        scraps = user["scraps"]
        vectors = {s["text"]: embedding_provider.embed(s["text"]) for s in scraps}

        run_lambda_sweep(user_name, scraps, vectors, attach_threshold=0.30, lambdas=lambdas)
        inspect_reassignments(user_name, scraps, vectors, attach_threshold=0.30, lam=0.3)


if __name__ == "__main__":
    main()
