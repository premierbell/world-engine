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


def find_split_candidates(
    islands: list[Island],
    vectors: dict[str, list[float]],
    min_cluster_size: int = 3,
    min_samples: int = 1,
    purity_threshold: float = 0.35,
    min_group_size: int = 3,
) -> dict[int, dict[int, list[Topic]]]:
    """Split Trigger + Split Plan (Finding #003 이후 신설). 실행은 apply_split()이
    따로 담당한다 - "Split한다"와 "Split 후보가 된다"를 분리한다. Merge보다
    훨씬 보수적으로 설계한다: Island가 갈라지면 사용자가 보던 섬이 둘로
    나뉘고 Label도 바뀌므로, 두 조건을 동시에 만족할 때만 후보로 삼는다.

    1. Island 전체 purity가 purity_threshold 미만 (전체적으로 애매하다)
    2. Island 내부 Topic들을 offline HDBSCAN 라벨로 묶었을 때, 스크랩
       min_group_size개 이상인 그룹이 2개 이상 나온다 (쪼갤 만한 진짜 구조가
       있다 - 그냥 노이즈로 갈라지는 게 아니다)

    확신이 없는 Topic(스크랩이 전부 HDBSCAN Noise)이거나 그룹 크기가
    min_group_size 미만인 Topic은 통째로 버리지 않는다 - 가장 큰(=survivor로
    남을) 그룹에 합쳐서 반환한다. Split은 "확신 있는 것만 떼어내고, 확신
    없는 건 원래 자리에 둔다"는 Minimum Change Principle을 데이터 유실 없이
    지켜야 한다.

    반환값: {island_id: {hdbscan_label: [해당 라벨이 dominant인 Topic들]}} -
    모든 그룹의 Topic 스크랩 총합은 원래 Island의 스크랩 총합과 같다.
    """
    all_texts = [text for isl in islands for topic in isl.topics for text in topic.scraps]
    matrix = normalize(np.array([vectors[text] for text in all_texts]))
    labels = HDBSCAN(
        min_cluster_size=min_cluster_size, min_samples=min_samples, metric="euclidean", copy=True
    ).fit_predict(matrix)
    label_of = dict(zip(all_texts, labels))

    candidates: dict[int, dict[int, list[Topic]]] = {}
    for isl in islands:
        island_texts = [text for topic in isl.topics for text in topic.scraps]
        island_labels = [label_of[text] for text in island_texts if label_of[text] != -1]
        if not island_labels:
            continue
        _, dominant_count = Counter(island_labels).most_common(1)[0]
        island_purity = dominant_count / len(island_texts)
        if island_purity >= purity_threshold:
            continue  # 이미 충분히 순수함 - Split 후보 아님

        groups: dict[int, list[Topic]] = defaultdict(list)
        no_signal: list[Topic] = []
        for topic in isl.topics:
            topic_labels = [label_of[text] for text in topic.scraps if label_of[text] != -1]
            if not topic_labels:
                no_signal.append(topic)  # 전부 Noise - 확신 없음, 나중에 survivor에 귀속
                continue
            dominant, _ = Counter(topic_labels).most_common(1)[0]
            groups[dominant].append(topic)

        significant_groups = {
            label: topics
            for label, topics in groups.items()
            if sum(len(t.scraps) for t in topics) >= min_group_size
        }
        if len(significant_groups) < 2:
            continue  # 쪼갤 만한 진짜 구조가 없음

        # 확신 없는 Topic들과 너무 작은 그룹은 가장 큰(=survivor) 그룹에 합쳐서
        # 유실 없이 반환한다
        largest_label = max(
            significant_groups, key=lambda label: sum(len(t.scraps) for t in significant_groups[label])
        )
        leftover = no_signal + [
            topic for label, topics in groups.items() if label not in significant_groups for topic in topics
        ]
        significant_groups[largest_label] = significant_groups[largest_label] + leftover

        candidates[isl.id] = significant_groups

    return candidates


def apply_split(
    islands: list[Island], candidates: dict[int, dict[int, list[Topic]]], vectors: dict[str, list[float]]
) -> list[Island]:
    """Split Plan을 실제로 실행한다 (Minimum Change Principle): 스크랩 수 기준
    가장 큰 그룹이 기존 Island에 남아 id와 identity_vector를 그대로 유지하고,
    나머지 그룹들만 새 Island로 떨어져 나간다. 새 Island의 identity_vector는
    그 그룹에 속한 스크랩들의 평균 벡터로 정한다 - 아직 실제 화면 좌표 시스템이
    없어서(map_layout.md는 설계만 있음) embedding 공간에서의 "근처"를 좌표
    대신 쓴다.

    Growth Point는 아직 구현되지 않았다(Step 7 보류) - 이 함수는 비율 분배
    로직을 포함하지 않는다.
    """
    next_id = (max(isl.id for isl in islands) + 1) if islands else 0
    result: list[Island] = []
    for isl in islands:
        if isl.id not in candidates:
            result.append(isl)
            continue

        groups = candidates[isl.id]
        largest_label = max(groups, key=lambda label: sum(len(t.scraps) for t in groups[label]))

        isl.topics = groups[largest_label]
        for i, topic in enumerate(isl.topics):
            topic.id = i
        result.append(isl)

        for label, topics in groups.items():
            if label == largest_label:
                continue
            for i, topic in enumerate(topics):
                topic.id = i
            new_texts = [text for topic in topics for text in topic.scraps]
            new_vector = np.mean([vectors[text] for text in new_texts], axis=0).tolist()
            new_island = Island(next_id, new_vector, new_texts[0])
            new_island.topics = topics
            result.append(new_island)
            next_id += 1

    return result


def run_night_batch(
    islands: list[Island],
    vectors: dict[str, list[float]],
    min_cluster_size: int = 3,
    min_samples: int = 1,
    merge_purity_threshold: float = 0.5,
    split_purity_threshold: float = 0.35,
    min_group_size: int = 3,
) -> list[Island]:
    """Night Batch 전체 사이클 (Finding #004 대응): Merge -> Split -> 재-Merge.

    Finding #004(Local Split can increase global Topic duplication)의 원인은
    `find_split_candidates`가 분리 대상 Island 하나만 보고, 그 조각이 세계에
    이미 존재하는 다른 Island와 겹치는지는 확인하지 않는다는 것이었다. Split을
    "새 Island를 확정하는 연산"이 아니라 "새 후보를 만드는 연산"으로 다시
    본다 - Split 직후 만들어진 조각들을 포함해 전체 Island 집합에 대해
    `night_batch`(Merge)를 한 번 더 돌려서, 방금 떨어져 나온 조각이 기존
    Island와 합쳐지는 게 더 나으면 다시 합친다.

    이건 완전한 "Candidate Generation -> Global Evaluation -> Apply" 재설계는
    아니다 - Merge를 반복 적용해서 같은 효과의 일부를 얻는 실용적인 절충이다.
    진짜 전역 최적화(목적함수: Topic Duplication 최소화, 제약: purity/좌표
    안정성/Minimum Change)는 아직 설계되지 않았다.
    """
    merged = night_batch(islands, vectors, min_cluster_size, min_samples, merge_purity_threshold)
    candidates = find_split_candidates(merged, vectors, min_cluster_size, min_samples, split_purity_threshold, min_group_size)
    split = apply_split(merged, candidates, vectors)
    return night_batch(split, vectors, min_cluster_size, min_samples, merge_purity_threshold)


def topic_graph_reconstruct(
    islands: list[Island],
    vectors: dict[str, list[float]],
    edge_threshold: float = 0.24,
) -> list[Island]:
    """Night Batch v2 (Finding #004 이후, `hybrid_architecture.md` "Night Batch v2"
    절 참고): Island가 아니라 Topic을 기본 단위로 삼아 세계를 다시 구성한다.

    Merge(v0 night_batch), Split(v0 find_split_candidates/apply_split),
    Boundary Topic Move를 각각 다른 연산으로 두지 않는다 - 전부 "Topic Graph가
    다시 연결되는 현상" 하나로 통일한다:

    1. 모든 Island의 모든 Topic을 모은다 (Island 소속은 무시).
    2. 모든 Topic 쌍의 center_vector cosine similarity를 계산해서
       edge_threshold 이상이면 두 Topic 사이에 edge를 긋는다.
    3. Union-Find로 Connected Component(=Topic Graph에서 서로 연결된 묶음)를
       찾는다.
    4. 각 Component가 새로운 Island가 된다.

    edge_threshold=0.24는 island_threshold(V0 baseline)를 잠정 재사용한
    값이다 - Topic-Topic 비교용으로 별도 검증된 threshold는 아직 없다.

    Invariant: Component의 Topic 집합이 기존 Island 하나와 정확히 같으면 그
    Island를 그대로 반환한다(id/identity_vector 불변 - 좌표 불변 원칙).
    바뀐 Component는 스크랩 수가 가장 많이 기여한 원래 Island의 id를
    물려받는다(Minimum Change Principle, v0와 동일 규칙).
    """
    all_topics = [topic for isl in islands for topic in isl.topics]
    topic_origin_island: dict[int, Island] = {}
    for isl in islands:
        for topic in isl.topics:
            topic_origin_island[id(topic)] = isl

    parent: dict[int, int] = {id(topic): id(topic) for topic in all_topics}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(len(all_topics)):
        for j in range(i + 1, len(all_topics)):
            sim = cosine_similarity(all_topics[i].center_vector, all_topics[j].center_vector)
            if sim >= edge_threshold:
                union(id(all_topics[i]), id(all_topics[j]))

    components: dict[int, list[Topic]] = defaultdict(list)
    for topic in all_topics:
        components[find(id(topic))].append(topic)

    original_topic_sets: dict[int, set[int]] = {isl.id: {id(t) for t in isl.topics} for isl in islands}

    result: list[Island] = []
    for topics in components.values():
        topic_ids = {id(t) for t in topics}
        unchanged_island = next((isl for isl in islands if original_topic_sets[isl.id] == topic_ids), None)
        if unchanged_island is not None:
            result.append(unchanged_island)
            continue

        contribution: dict[int, int] = defaultdict(int)
        for topic in topics:
            contribution[topic_origin_island[id(topic)].id] += len(topic.scraps)
        survivor_id = max(contribution, key=lambda island_id: contribution[island_id])

        for i, topic in enumerate(topics):
            topic.id = i
        new_texts = [text for topic in topics for text in topic.scraps]
        new_vector = np.mean([vectors[text] for text in new_texts], axis=0).tolist()
        new_island = Island(survivor_id, new_vector, new_texts[0])
        new_island.topics = topics
        result.append(new_island)

    return result