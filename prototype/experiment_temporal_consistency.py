"""Experiment #41: Temporal Consistency Analysis (관측 실험, 알고리즘 변경 없음).

Research Question #7("Topic Identity는 복원 대상인가, 형성되는 대상인가?")
첫 실험. Finding #008/#009/#010은 전부 "단일 관측(Observation x 1)으로
Identity를 즉시 복원하려는 시도"의 실패였다 - cosine 하나, 태그 겹침
하나, 그래프 연결 하나로 "이게 같은 Topic이다"를 한 번에 판단하려 했다.

H1(사실상 증명됨): Topic Identity는 단일 관측으로 복원되지 않는다.
H2(이번 실험이 검증할 것): 반복 관측은 Identity 자체가 아니라 Identity에
대한 Confidence를 증가시킨다 - 즉, 같은 실제 Topic의 새 candidate가
여러 Night Batch에 걸쳐 반복적으로 나타날 때, 그때마다 "가장 가까운
Anchor"로 뽑히는 대상이 흔들리지 않고 일관되게 유지되는가?

이 실험은 알고리즘을 만들지 않는다(Confidence 시스템을 구현하지 않음).
Day1로 Anchor를 만들고, Day7/Day30 두 번의 독립된 관측 시점에서
`compute_assignment_matrix()`(순수 관찰용, night_batch_anchor의 attach
결정은 여전히 그대로 실행해서 Day30 시점 Anchor 상태를 현실적으로
재현)로 각 실제 Topic이 어떤 Anchor를 1순위로 가리키는지만 기록하고,
Day7 vs Day30에서 그 1순위가 같은 Anchor인지 비교한다.
"""

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


def dominant_topic(texts: list[str], text_to_topic: dict[str, str]) -> str:
    return Counter(text_to_topic[t] for t in texts).most_common(1)[0][0]


def observe_batch(
    islands: list[Island], day_texts: list[str], vectors: dict[str, list[float]], text_to_topic: dict[str, str]
) -> dict[str, tuple[int, float, int]]:
    """이 배치의 candidate들을 실제 Topic별로 묶어서, 각 Topic이 1순위로 가리키는
    Anchor id/score/그 선택에 동의한 candidate 수를 반환한다. 순수 관찰만 하고
    Island 상태는 바꾸지 않는다."""
    candidates, anchors, matrix = compute_assignment_matrix(islands, day_texts, vectors)
    if not candidates or not anchors:
        return {}

    topic_votes: dict[str, Counter] = defaultdict(Counter)
    topic_scores: dict[str, list[float]] = defaultdict(list)
    for texts, row in zip(candidates, matrix):
        topic = dominant_topic(texts, text_to_topic)
        best_idx = max(range(len(row)), key=lambda i: row[i])
        topic_votes[topic][anchors[best_idx].id] += 1
        topic_scores[topic].append(row[best_idx])

    result: dict[str, tuple[int, float, int]] = {}
    for topic, votes in topic_votes.items():
        winner_id, agree_count = votes.most_common(1)[0]
        avg_score = sum(topic_scores[topic]) / len(topic_scores[topic])
        result[topic] = (winner_id, avg_score, agree_count)
    return result


def run_persona(user_name: str, scraps: list[dict], vectors: dict[str, list[float]], attach_threshold: float) -> None:
    text_to_topic = {s["text"]: s["topic"] for s in scraps}
    days = sorted({s["day"] for s in scraps})
    assert days[0] == min(days)

    islands: list[Island] = []
    observations: dict[int, dict[str, tuple[int, float, int]]] = {}

    for day in days:
        day_texts = [s["text"] for s in scraps if s["day"] == day]
        if islands:
            observations[day] = observe_batch(islands, day_texts, vectors, text_to_topic)
        islands = night_batch_anchor(islands, day_texts, vectors, attach_threshold=attach_threshold)

    observed_days = [d for d in days if d in observations]
    if len(observed_days) < 2:
        console.print(f"[dim]{user_name}: 비교 가능한 관측 시점이 2개 미만 - 생략[/dim]")
        return

    d1, d2 = observed_days[0], observed_days[-1]
    obs1, obs2 = observations[d1], observations[d2]
    common_topics = sorted(set(obs1) & set(obs2))

    table = Table(title=f"Experiment #41: Temporal Consistency (Day{d1} vs Day{d2}, {user_name})")
    for col in ("실제 Topic", f"Day{d1} 1순위 Anchor", f"Day{d1} score", f"Day{d2} 1순위 Anchor", f"Day{d2} score", "일관됨?"):
        table.add_column(col)

    consistent = 0
    for topic in common_topics:
        (id1, score1, _), (id2, score2, _) = obs1[topic], obs2[topic]
        same = id1 == id2
        consistent += same
        table.add_row(topic, str(id1), f"{score1:.3f}", str(id2), f"{score2:.3f}", "O" if same else "X")

    console.print(table)
    console.print(
        f"  [bold]일관되게 같은 Anchor를 1순위로 선택한 Topic: "
        f"{consistent}/{len(common_topics)}[/bold]\n"
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

        run_persona(user_name, scraps, vectors, attach_threshold=0.30)


if __name__ == "__main__":
    main()
