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

from collections import Counter, defaultdict
from dataclasses import dataclass

import numpy as np
from sklearn.cluster import HDBSCAN
from sklearn.preprocessing import normalize

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


def assign_scrap_topic_first(islands: list[Island], vector: list[float], text: str, config: dict) -> AssignmentTrace:
    """Topic-First 변형: Island identity_vector 대신, 세상에 존재하는 모든 Topic과
    먼저 비교한다. Topic이 Island보다 세밀하므로, 이 편입 판단이 더 global structure를
    반영할 것이라는 가설(Experiment #11)을 검증하기 위한 변형이다.
    """
    alpha = config["ema_alpha"]
    island_threshold = config["island_threshold"]
    topic_threshold = config["topic_threshold"]

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

    # 1. 모든 Island의 모든 Topic과 비교 (Island 단위가 아니라 Topic 단위)
    topic_candidates = [
        (isl, topic, cosine_similarity(vector, topic.center_vector))
        for isl in islands
        for topic in isl.topics
    ]
    best_island, best_topic, best_topic_sim = max(topic_candidates, key=lambda c: c[2])

    if best_topic_sim >= topic_threshold:
        best_island.growth_vector = ema_update(best_island.growth_vector, vector, alpha)
        best_topic.add(vector, text, alpha)
        return AssignmentTrace(
            text=text,
            island_similarities=[(isl.id, cosine_similarity(vector, isl.identity_vector)) for isl in islands],
            chosen_island_id=best_island.id,
            chosen_similarity=cosine_similarity(vector, best_island.identity_vector),
            island_threshold=island_threshold,
            island_decision="MERGE_VIA_TOPIC",
            identity_stability=best_island.identity_stability,
            topic_id=best_topic.id,
            topic_similarity=best_topic_sim,
            topic_decision="MERGE",
        )

    # 2. 어떤 Topic도 못 넘으면 기존처럼 Island identity_vector로 폴백
    island_similarities = [(isl.id, cosine_similarity(vector, isl.identity_vector)) for isl in islands]
    best_id, best_sim = max(island_similarities, key=lambda pair: pair[1])

    if best_sim >= island_threshold:
        best_island = next(isl for isl in islands if isl.id == best_id)
        topic_id, topic_sim, topic_decision = best_island.add(vector, text, alpha, topic_threshold)
        return AssignmentTrace(
            text=text,
            island_similarities=island_similarities,
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
        island_similarities=island_similarities,
        chosen_island_id=new_island_id,
        chosen_similarity=best_sim,
        island_threshold=island_threshold,
        island_decision="CREATE_ISLAND",
        identity_stability=1.0,
    )


def night_batch(
    islands: list[Island],
    vectors: dict[str, list[float]],
    min_cluster_size: int = 3,
    min_samples: int = 1,
    purity_threshold: float = 0.5,
) -> list[Island]:
    """Night Batch v0 - Merge만 수행한다 (hybrid_architecture.md 5단계 중 1/2/5:
    후보 탐색, Merge 후보, Minimum Change 필터). Split, Boundary Topic 이동은
    다음 버전 과제로 남긴다.

    offline HDBSCAN(Experiment #12/#15에서 검증된 방식)을 "참고 자료"로만
    쓴다 - HDBSCAN이 만든 클러스터를 그대로 세계에 덮어씌우지 않고, 현재
    Island들 중 HDBSCAN에서 같은 클러스터로 몰리는(purity가 높은) 쌍만 골라
    합친다. 이게 Minimum Change Principle(Invariant #5)을 코드로 구현한
    부분이다 - 애매한 후보(purity가 낮은 Island)는 그대로 둔다.

    Growth Point는 아직 구현되지 않았다(Step 7 보류) - 이 함수는 그 부분은
    건드리지 않는다.
    """
    all_texts = [text for isl in islands for topic in isl.topics for text in topic.scraps]
    matrix = normalize(np.array([vectors[text] for text in all_texts]))
    labels = HDBSCAN(
        min_cluster_size=min_cluster_size, min_samples=min_samples, metric="euclidean", copy=True
    ).fit_predict(matrix)
    label_of = dict(zip(all_texts, labels))

    # 각 Island의 "다수결 HDBSCAN 라벨"과 그 비율(purity)을 계산
    dominant_label: dict[int, int] = {}
    purity: dict[int, float] = {}
    for isl in islands:
        texts = [text for topic in isl.topics for text in topic.scraps]
        island_labels = [label_of[text] for text in texts if label_of[text] != -1]
        if not island_labels:
            continue
        label, count = Counter(island_labels).most_common(1)[0]
        dominant_label[isl.id] = label
        purity[isl.id] = count / len(texts)

    # 같은 다수결 라벨을 공유하고 purity가 임계값 이상인 Island들만 merge 후보로 묶는다
    groups: dict[int, list[Island]] = defaultdict(list)
    for isl in islands:
        if isl.id in dominant_label and purity[isl.id] >= purity_threshold:
            groups[dominant_label[isl.id]].append(isl)

    merged_ids: set[int] = set()
    for group in groups.values():
        if len(group) < 2:
            continue
        survivor = min(group, key=lambda isl: isl.id)  # Invariant #2: 오래된(ID가 작은) Island가 생존
        for isl in group:
            if isl.id == survivor.id:
                continue
            offset = len(survivor.topics)
            for i, topic in enumerate(isl.topics):
                topic.id = offset + i
            survivor.topics.extend(isl.topics)
            merged_ids.add(isl.id)

    return [isl for isl in islands if isl.id not in merged_ids]