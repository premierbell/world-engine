"""Experiment #34: Does Objective v0 actually improve real-world quality?

Experiment #33은 "J(local search) > J(greedy)"만 확인했다 - 목적함수 값이
개선됐다는 것이지, 실제 Island 구조의 Topic Purity/Duplication Rate가
개선됐는지는 한 번도 측정하지 않았다(사용자가 명시적으로 지적한 미해결
질문). 이 실험은 그 간극을 메운다: Objective v0(Experiment #33)로 찾은
재배정을 실제로 World 상태에 반영해서 Day1→7→30 전체 증분 시나리오를
끝까지 돌리고, Experiment #28과 같은 지표(Island 수, Topic Purity, Topic
Duplication Rate)로 Greedy(night_batch_anchor 그대로)와 직접 비교한다.

world.py는 건드리지 않는다 - Objective v0/Local Search는 여전히 순수
실험 단계이지 프로덕션 후보로 승격된 게 아니다(Research Question #3
미해결). 이 실험도 "Objective v0가 정답이다"를 증명하려는 게 아니라,
"J 개선이 실제 품질 개선과 방향이 같은지"부터 확인하는 진단이다.
"""

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from experiment_anchor_model import island_purity_weighted, load_virtual_user, topic_duplication_rate
from experiment_batch_objective import NEW, candidate_centroid, greedy_assignment, local_search
from world import Island, compute_assignment_matrix, night_batch_anchor

console = Console()


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def apply_assignment(
    islands: list[Island],
    candidates: list[list[str]],
    assignment: list[int],
    anchors: list[Island],
    vectors: dict[str, list[float]],
) -> list[Island]:
    """local_search가 찾은 배정을 실제 Island 상태에 반영한다 - night_batch_anchor의
    attach()/새 Island 생성과 동일한 규칙, 대상만 Greedy가 아니라 주어진 assignment."""
    result = list(islands)
    next_id = max((isl.id for isl in islands), default=-1) + 1
    for texts, a in zip(candidates, assignment):
        if a == NEW:
            centroid = candidate_centroid(texts, vectors)
            new_island = Island(next_id, centroid, texts[0])
            new_island.topics[0].scraps = list(texts)
            result.append(new_island)
            next_id += 1
        else:
            anchors[a].topics[0].scraps.extend(texts)
    return result


def run_greedy(scraps: list[dict], vectors: dict[str, list[float]], attach_threshold: float) -> list[Island]:
    islands: list[Island] = []
    for day in sorted({s["day"] for s in scraps}):
        day_texts = [s["text"] for s in scraps if s["day"] == day]
        islands = night_batch_anchor(islands, day_texts, vectors, attach_threshold=attach_threshold)
    return islands


def run_objective_v0(
    scraps: list[dict], vectors: dict[str, list[float]], attach_threshold: float, lam: float
) -> list[Island]:
    """Day1(첫 배치, 비교 대상 Anchor가 아직 없음)은 night_batch_anchor로 그대로
    처리 - Greedy와 Objective v0가 다를 수 있는 지점은 Anchor가 생긴 이후뿐이다.
    Day7/Day30부터는 compute_assignment_matrix + local_search(Objective v0)로
    찾은 배정을 적용한다."""
    islands: list[Island] = []
    for day in sorted({s["day"] for s in scraps}):
        day_texts = [s["text"] for s in scraps if s["day"] == day]
        if not islands:
            islands = night_batch_anchor(islands, day_texts, vectors, attach_threshold=attach_threshold)
            continue
        candidates, anchors, matrix = compute_assignment_matrix(islands, day_texts, vectors)
        if not candidates:
            continue
        centroids = [candidate_centroid(texts, vectors) for texts in candidates]
        greedy = greedy_assignment(matrix, attach_threshold)
        improved, _ = local_search(greedy, candidates, matrix, centroids, attach_threshold, lam)
        islands = apply_assignment(islands, candidates, improved, anchors, vectors)
    return islands


def run_quality_sweep(user_name: str, scraps: list[dict], vectors: dict, attach_threshold: float, lambdas: list[float]) -> None:
    text_to_topic = {s["text"]: s["topic"] for s in scraps}

    table = Table(title=f"Experiment #34: Objective v0 적용 시 실제 품질 변화 ({user_name})")
    for col in ("방식", "Island 수", "중복 주제/전체", "중복률", "Purity"):
        table.add_column(col)

    greedy_islands = run_greedy(scraps, vectors, attach_threshold)
    rate, dup, total = topic_duplication_rate(greedy_islands, text_to_topic)
    purity = island_purity_weighted(greedy_islands, text_to_topic)
    table.add_row("Greedy (night_batch_anchor)", str(len(greedy_islands)), f"{dup}/{total}", f"{rate:.1%}", f"{purity:.3f}")

    for lam in lambdas:
        islands = run_objective_v0(scraps, vectors, attach_threshold, lam)
        rate, dup, total = topic_duplication_rate(islands, text_to_topic)
        purity = island_purity_weighted(islands, text_to_topic)
        table.add_row(f"Objective v0 (λ={lam:.2f})", str(len(islands)), f"{dup}/{total}", f"{rate:.1%}", f"{purity:.3f}")

    console.print(table)
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

        run_quality_sweep(user_name, scraps, vectors, attach_threshold=0.30, lambdas=lambdas)


if __name__ == "__main__":
    main()
