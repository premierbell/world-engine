"""World Engine core - Island/Topic assignment logic.

ai_rules.md Rule 4(Nearest Neighbor) + Rule 5(Threshold) + Rule 6(Center Vector Update, EMA)
+ Rule 7(Topic Discovery)를 구현한다. AI는 임베딩만 주고, 여기서부터는 전부 결정론적 알고리즘이다.

Island는 두 개의 벡터를 갖는다:
- identity_vector: 섬의 정체성. 생성 시점에 고정되고 절대 갱신되지 않는다.
  새 스크랩이 이 섬에 속하는지 판단할 때는 반드시 이 벡터와 비교한다.
- growth_vector: 섬이 성장해온 흐름(EMA). 추천/애니메이션 등 "요즘 어떤 방향인가"가
  필요한 곳에만 쓰고, Island 편입 판단에는 절대 쓰지 않는다.

identity_vector와 growth_vector의 코사인 유사도가 Identity Stability다 - 섬이
정체성에서 얼마나 멀어졌는지(drift)를 보여주는 지표 (evaluation_metrics.md).
"""

from dataclasses import dataclass

import numpy as np

from similarity import cosine_similarity


def ema_update(old_vector: list[float], new_vector: list[float], alpha: float) -> list[float]:
    old = np.array(old_vector)
    new = np.array(new_vector)
    return (alpha * new + (1 - alpha) * old).tolist()


class Topic:
    def __init__(self, topic_id: int, vector: list[float], text: str):
        self.id = topic_id
        self.center_vector = vector
        self.scraps = [text]

    def add(self, vector: list[float], text: str, alpha: float) -> None:
        self.center_vector = ema_update(self.center_vector, vector, alpha)
        self.scraps.append(text)


class Island:
    def __init__(self, island_id: int, vector: list[float], text: str):
        self.id = island_id
        self.identity_vector = vector  # 절대 갱신 안 함 - Island 편입 판단 기준
        self.growth_vector = vector  # EMA로 계속 갱신 - 성장 트렌드 (판단에는 안 씀)
        self.topics: list[Topic] = [Topic(0, vector, text)]

    @property
    def identity_stability(self) -> float:
        return cosine_similarity(self.identity_vector, self.growth_vector)

    def add(self, vector: list[float], text: str, alpha: float, topic_threshold: float) -> tuple[int, float, str]:
        self.growth_vector = ema_update(self.growth_vector, vector, alpha)
        best_topic = max(self.topics, key=lambda t: cosine_similarity(vector, t.center_vector))
        topic_sim = cosine_similarity(vector, best_topic.center_vector)
        if topic_sim >= topic_threshold:
            best_topic.add(vector, text, alpha)
            return best_topic.id, topic_sim, "MERGE"
        new_topic = Topic(len(self.topics), vector, text)
        self.topics.append(new_topic)
        return new_topic.id, topic_sim, "CREATE"


@dataclass
class AssignmentTrace:
    text: str
    island_similarities: list[tuple[int, float]]
    chosen_island_id: int
    chosen_similarity: float | None
    island_threshold: float
    island_decision: str
    identity_stability: float | None
    topic_id: int | None = None
    topic_similarity: float | None = None
    topic_decision: str | None = None


def assign_scrap(islands: list[Island], vector: list[float], text: str, config: dict) -> AssignmentTrace:
    alpha = config["ema_alpha"]
    island_threshold = config["island_threshold"]
    topic_threshold = config["topic_threshold"]

    # 판단 기준은 growth_vector가 아니라 identity_vector
    similarities = [(isl.id, cosine_similarity(vector, isl.identity_vector)) for isl in islands]

    if not islands:
        islands.append(Island(0, vector, text))
        return AssignmentTrace(
            text=text,
            island_similarities=[],
            chosen_island_id=0,
            chosen_similarity=None,
            island_threshold=island_threshold,
            island_decision="CREATE_ISLAND",
            identity_stability=1.0,
        )

    best_id, best_sim = max(similarities, key=lambda pair: pair[1])

    if best_sim >= island_threshold:
        best_island = next(isl for isl in islands if isl.id == best_id)
        topic_id, topic_sim, topic_decision = best_island.add(vector, text, alpha, topic_threshold)
        return AssignmentTrace(
            text=text,
            island_similarities=similarities,
            chosen_island_id=best_id,
            chosen_similarity=best_sim,
            island_threshold=island_threshold,
            island_decision="MERGE",
            identity_stability=best_island.identity_stability,
            topic_id=topic_id,
            topic_similarity=topic_sim,
            topic_decision=topic_decision,
        )

    new_island_id = len(islands)
    islands.append(Island(new_island_id, vector, text))
    return AssignmentTrace(
        text=text,
        island_similarities=similarities,
        chosen_island_id=new_island_id,
        chosen_similarity=best_sim,
        island_threshold=island_threshold,
        island_decision="CREATE_ISLAND",
        identity_stability=1.0,
    )
