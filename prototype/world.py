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

    return _rebuild_islands_from_components(islands, list(components.values()), vectors)


def topic_graph_reconstruct_hdbscan(
    islands: list[Island],
    vectors: dict[str, list[float]],
    min_cluster_size: int = 2,
    min_samples: int = 1,
) -> list[Island]:
    """Night Batch v2, 변형 A: Connectivity를 HDBSCAN으로 교체한 버전
    (Experiment #25, Finding #004 대응). `topic_graph_reconstruct`(pairwise
    threshold + Union-Find)가 체이닝으로 실패한 뒤 만든 버전이다 - 2~3단계
    (Topic Graph 생성 -> Connected Component)만 Topic의 center_vector에
    대한 HDBSCAN 클러스터링으로 바꾸고, 나머지(Invariant 유지, Island
    재구성)는 동일하다.

    **Experiment #25 결과: 기각.** 온라인 단계가 Topic을 21~27개까지 잘게
    만들어서(스크랩 71개 기준 Topic당 평균 3개 미만) 밀도 추정 자체가
    불안정하다 - 어떤 min_cluster_size에서도 Backend User가 12개 이상으로
    쪼개진다(원래 Merge-only의 1개보다 훨씬 나쁨). Topic의 center_vector를
    직접 클러스터링하는 대신 `topic_graph_reconstruct_scrap_informed`(변형
    B)를 시도했지만 그것도 완전히는 해결하지 못했다 - Finding #005
    (Aggregation Level Trade-off) 참고. 코드는 그 근거로 남긴다.

    Noise(-1)로 분류된 Topic은 각자 독립된 Component(=자기 혼자만의 새
    Island)가 된다 - Experiment #12/#22와 같은 정책(noise를 억지로 하나로
    묶지 않는다).
    """
    all_topics = [topic for isl in islands for topic in isl.topics]
    matrix = normalize(np.array([topic.center_vector for topic in all_topics]))
    labels = HDBSCAN(
        min_cluster_size=min_cluster_size, min_samples=min_samples, metric="euclidean", copy=True
    ).fit_predict(matrix)

    components: dict[int, list[Topic]] = defaultdict(list)
    next_noise_id = int(labels.max()) + 1 if len(labels) else 0
    for topic, label in zip(all_topics, labels):
        if label == -1:
            components[next_noise_id].append(topic)
            next_noise_id += 1
        else:
            components[int(label)].append(topic)

    return _rebuild_islands_from_components(islands, list(components.values()), vectors)


def topic_graph_reconstruct_scrap_informed(
    islands: list[Island],
    vectors: dict[str, list[float]],
    min_cluster_size: int = 5,
    min_samples: int = 1,
) -> list[Island]:
    """Night Batch v2, 변형 B: Topic의 center_vector 대신, 이미 검증된 scrap
    레벨 HDBSCAN(Experiment #12/#15/#22)의 클러스터 라벨을 참고해서 Topic을
    재그룹화한다 - Topic 자체가 표본이 너무 적어(변형 A 참고) 직접
    클러스터링하기 불안정하다는 문제를 피하려는 시도다. 각 Topic은 자기
    스크랩들이 scrap 레벨에서 다수결로 속한 클러스터에 따라 그룹화된다.

    **Experiment #25 결과: 부분 개선, 완전 해결은 아님.** AI Researcher는
    개선됐지만(최선 5개 Island, 2/9 중복) Backend User가 오히려
    나빠졌다(최선 7개, 4/9 중복 - 원래 Merge-only의 1개/0%보다 나쁨). 원인은
    scrap 레벨 HDBSCAN 자체가 Backend User를 완벽한 1개 클러스터로 만들지
    않기 때문이다("58+7+noise 6") - Island 단위 다수결에서는 여러 Topic의
    스크랩이 뭉뚱그려지며 이 노이즈가 평균화되지만, Topic 단위로 내리면
    노이즈가 그대로 드러난다. Finding #005(Aggregation Level Trade-off)의
    핵심 근거다.
    """
    all_texts = [text for isl in islands for topic in isl.topics for text in topic.scraps]
    matrix = normalize(np.array([vectors[text] for text in all_texts]))
    labels = HDBSCAN(
        min_cluster_size=min_cluster_size, min_samples=min_samples, metric="euclidean", copy=True
    ).fit_predict(matrix)
    label_of = dict(zip(all_texts, labels))

    all_topics = [topic for isl in islands for topic in isl.topics]
    components: dict[int, list[Topic]] = defaultdict(list)
    next_noise_id = int(labels.max()) + 1 if len(labels) else 0
    for topic in all_topics:
        topic_labels = [label_of[text] for text in topic.scraps if label_of[text] != -1]
        if not topic_labels:
            components[next_noise_id].append(topic)
            next_noise_id += 1
            continue
        dominant, _ = Counter(topic_labels).most_common(1)[0]
        components[dominant].append(topic)

    return _rebuild_islands_from_components(islands, list(components.values()), vectors)


def _rebuild_islands_from_components(
    islands: list[Island], components: list[list[Topic]], vectors: dict[str, list[float]]
) -> list[Island]:
    """Topic Graph 계열 함수들이 공유하는 Invariant 유지 로직. Component의
    Topic 집합이 기존 Island 하나와 정확히 같으면 그대로 반환하고(좌표 불변),
    바뀐 Component는 스크랩 수 기여가 가장 큰 원래 Island의 id를 물려받는다
    (Minimum Change Principle) - 단, 그 id가 이미 다른 Component에 쓰였다면
    (원래 하나의 Island가 여러 Component로 흩어진 경우) 새 id를 발급한다.
    Island id는 세계 전체에서 유일해야 한다.
    """
    topic_origin_island: dict[int, Island] = {}
    for isl in islands:
        for topic in isl.topics:
            topic_origin_island[id(topic)] = isl
    original_topic_sets: dict[int, set[int]] = {isl.id: {id(t) for t in isl.topics} for isl in islands}

    next_id = (max(isl.id for isl in islands) + 1) if islands else 0
    used_ids: set[int] = set()
    result: list[Island] = []
    for topics in components:
        topic_ids = {id(t) for t in topics}
        unchanged_island = next((isl for isl in islands if original_topic_sets[isl.id] == topic_ids), None)
        if unchanged_island is not None:
            result.append(unchanged_island)
            used_ids.add(unchanged_island.id)
            continue

        contribution: dict[int, int] = defaultdict(int)
        for topic in topics:
            contribution[topic_origin_island[id(topic)].id] += len(topic.scraps)
        survivor_id = max(contribution, key=lambda island_id: contribution[island_id])
        if survivor_id in used_ids:
            survivor_id = next_id
            next_id += 1
        used_ids.add(survivor_id)

        for i, topic in enumerate(topics):
            topic.id = i
        new_texts = [text for topic in topics for text in topic.scraps]
        new_vector = np.mean([vectors[text] for text in new_texts], axis=0).tolist()
        new_island = Island(survivor_id, new_vector, new_texts[0])
        new_island.topics = topics
        result.append(new_island)

    return result


def selective_night_batch(
    islands: list[Island],
    vectors: dict[str, list[float]],
    min_cluster_size: int = 5,
    min_samples: int = 1,
    purity_threshold: float = 0.5,
    min_group_size: int = 3,
) -> list[Island]:
    """Night Batch v3 (Finding #005 대응): 세계 전체를 재구성하지 않는다.

    오늘까지의 시도(Split, Union-Find Topic Graph, Topic-level HDBSCAN)는
    전부 세계 전체를 다시 만들었고, 그때마다 이미 좋았던 Island(Backend
    User)까지 건드려서 나빠졌다. v0 Merge가 Backend User에서 잘 작동했던
    이유를 돌아보면 - **애초에 purity 높은 Island만 후보로 삼고 나머지는
    그대로 뒀기 때문**이었다. 이 원칙을 명시적인 설계로 승격한다:

    1. Scrap 레벨 HDBSCAN(참고 자료, Experiment #12/#22와 동일 방법론)을
       한 번 계산해서 각 Island의 다수결 라벨/purity를 구한다.
    2. purity >= threshold인 "건강한" Island: Merge 후보로만 검토(v0
       `night_batch`와 동일 로직). 매칭되는 짝이 없으면 완전히 그대로
       반환한다 - 재계산도, 재라벨링도 안 한다.
    3. purity < threshold인 "의심스러운" Island만 Split 후보로 검토한다.
       단, Finding #004(local split이 global 중복을 늘림)의 교훈대로,
       분리된 조각을 곧바로 새 Island로 만들지 않는다 - 그 조각의 다수결
       라벨이 이미 확정된(건강한, 또는 이번에 먼저 처리된) 다른 Island와
       같으면 그 Island에 흡수시키고, 일치하는 게 없을 때만 새 Island를
       만든다.
    """
    all_texts = [text for isl in islands for topic in isl.topics for text in topic.scraps]
    matrix = normalize(np.array([vectors[text] for text in all_texts]))
    labels = HDBSCAN(
        min_cluster_size=min_cluster_size, min_samples=min_samples, metric="euclidean", copy=True
    ).fit_predict(matrix)
    label_of = dict(zip(all_texts, labels))

    def island_dominant(isl: Island) -> tuple[int | None, float]:
        texts = [text for topic in isl.topics for text in topic.scraps]
        island_labels = [label_of[text] for text in texts if label_of[text] != -1]
        if not island_labels:
            return None, 0.0
        label, count = Counter(island_labels).most_common(1)[0]
        return label, count / len(texts)

    healthy: list[Island] = []
    suspicious: list[Island] = []
    for isl in islands:
        _, purity = island_dominant(isl)
        (healthy if purity >= purity_threshold else suspicious).append(isl)

    merged_healthy = night_batch(healthy, vectors, min_cluster_size, min_samples, purity_threshold)

    label_to_island: dict[int, Island] = {}
    for isl in merged_healthy:
        label, purity = island_dominant(isl)
        if label is not None and purity >= purity_threshold:
            label_to_island[label] = isl

    next_id = (max(isl.id for isl in islands) + 1) if islands else 0
    result: list[Island] = list(merged_healthy)

    for isl in suspicious:
        groups: dict[int, list[Topic]] = defaultdict(list)
        no_signal: list[Topic] = []
        for topic in isl.topics:
            topic_labels = [label_of[text] for text in topic.scraps if label_of[text] != -1]
            if not topic_labels:
                no_signal.append(topic)
                continue
            dominant, _ = Counter(topic_labels).most_common(1)[0]
            groups[dominant].append(topic)

        significant_groups = {
            label: topics
            for label, topics in groups.items()
            if sum(len(t.scraps) for t in topics) >= min_group_size
        }
        if len(significant_groups) < 2:
            result.append(isl)  # 쪼갤 만한 구조가 없음 - 그대로 둔다
            continue

        largest_label = max(
            significant_groups, key=lambda label: sum(len(t.scraps) for t in significant_groups[label])
        )
        leftover = no_signal + [
            topic for label, topics in groups.items() if label not in significant_groups for topic in topics
        ]
        significant_groups[largest_label] = significant_groups[largest_label] + leftover

        for label, topics in significant_groups.items():
            if label in label_to_island:
                target = label_to_island[label]
                offset = len(target.topics)
                for i, topic in enumerate(topics):
                    topic.id = offset + i
                target.topics.extend(topics)
                continue

            for i, topic in enumerate(topics):
                topic.id = i
            if label == largest_label:
                isl.topics = topics
                result.append(isl)
                label_to_island[label] = isl
            else:
                new_texts = [text for topic in topics for text in topic.scraps]
                new_vector = np.mean([vectors[text] for text in new_texts], axis=0).tolist()
                new_island = Island(next_id, new_vector, new_texts[0])
                new_island.topics = topics
                result.append(new_island)
                label_to_island[label] = new_island
                next_id += 1

    return result


@dataclass
class AttachTrace:
    """night_batch_anchor의 attach/create 판단 근거를 그대로 남긴다(Experiment
    #29, Margin 가설 진단용) - ground truth 비교/정답 판정은 여기서 하지 않는다
    (ai_rules.md Rule 1: 알고리즘은 판단만, 정답 채점은 실험 스크립트 몫)."""

    texts: list[str]
    best_anchor_id: int | None
    best_similarity: float
    second_similarity: float | None
    margin: float | None
    decision: str  # "ATTACH" | "CREATE"
    attach_threshold: float
    anchor_scraps_before: list[str] | None = None  # ATTACH일 때만: 편입 직전 Anchor 구성 스냅샷


def night_batch_anchor(
    confirmed_islands: list[Island],
    new_scrap_texts: list[str],
    vectors: dict[str, list[float]],
    min_cluster_size: int = 3,
    min_samples: int = 1,
    attach_threshold: float = 0.5,
    trace: list[AttachTrace] | None = None,
    member_topk: int | None = None,
) -> list[Island]:
    """Anchor Model(`docs/anchor_model.md`)의 Island-level Night Batch
    구현(v0). `confirmed_islands`(Anchor)는 routine 상황에서 절대 수정하지
    않고 Context로만 쓴다 - identity_vector를 참고 기준으로만 비교하고,
    이 함수 안에서 기존 Anchor의 identity_vector/id는 바뀌지 않는다.

    `new_scrap_texts`(아직 Confirmed 안 된 스크랩)는 Greedy가 어디
    두었었는지 완전히 무시하고 scrap 레벨에서 원점 HDBSCAN으로 다시
    클러스터링한다. 각 클러스터는 **이번 배치 시작 시점의 고정된 Anchor
    목록**(`confirmed_islands`)과만 비교한다 — 배치 도중 새로 만들어진
    Anchor를 다른 클러스터가 다시 비교 대상으로 삼지 않는다. 이걸
    허용하면 방금 생긴 큰 Anchor가 "허브"가 되어 뒤에 처리되는 클러스터를
    전부 끌어당기는 체이닝(Finding #004, Evidence 3)이 그대로
    재현된다 - 비교 기준을 배치 시작 시점 스냅샷으로 고정하는 게
    이 함수의 핵심이다. attach_threshold 이상이면 그 Anchor에
    편입(Attach)하고, 아니면 새 Anchor를 만든다(배치 내 새 Anchor끼리는
    서로 합쳐지지 않는다 - 다음 Night Batch에서 스스로를 다시 Context로
    참고하며 자연스럽게 정리될 기회를 갖는다).

    Topic 세부 구조(Step 5.25, Topic 레벨 Anchor)는 이번 v0 구현에서는
    단순화해서 클러스터/Anchor 하나당 Topic 하나로 취급한다 - Topic
    레벨까지 온전히 구현하는 것은 다음 단계 과제다.

    `trace`(선택)가 주어지면 매 attach/create 판단마다 AttachTrace를
    append한다 - best/second 유사도와 margin을 그대로 남기고, 그게
    "좋은 판단"이었는지는 정하지 않는다(ground truth 채점은 실험
    스크립트 몫, Experiment #29).

    `member_topk`(선택, Research Question #2 / Finding #007): None이면
    기존과 동일하게 Anchor의 identity_vector(단일 centroid)와 비교한다.
    정수를 주면 대신 Anchor에 속한 멤버 벡터들과 새 클러스터 centroid의
    유사도를 개별로 계산해서, 그중 상위 k개(멤버 수가 k보다 적으면
    전부)의 평균을 그 Anchor의 점수로 쓴다(Experiment #30에서 사후
    진단으로만 확인했던 top-k averaging을 실제 attach 판단 기준으로
    승격) - 아직 v0/실험 단계이므로 매 비교마다 멤버 전체를 순회한다
    (계산 비용 최적화는 하지 않음, Finding #007 Implication 참고).
    """
    if not new_scrap_texts:
        return list(confirmed_islands)

    matrix = normalize(np.array([vectors[text] for text in new_scrap_texts]))
    labels = HDBSCAN(
        min_cluster_size=min_cluster_size, min_samples=min_samples, metric="euclidean", copy=True
    ).fit_predict(matrix)

    clusters: dict[int, list[str]] = defaultdict(list)
    for text, label in zip(new_scrap_texts, labels):
        clusters[label].append(text)

    original_anchors: list[Island] = list(confirmed_islands)  # 비교 기준 스냅샷 - 배치 중 안 자란다
    result: list[Island] = list(confirmed_islands)
    next_id = (max((isl.id for isl in confirmed_islands), default=-1)) + 1

    def anchor_score(centroid: list[float], anchor: Island) -> float:
        if member_topk is None:
            return cosine_similarity(centroid, anchor.identity_vector)
        member_sims = sorted(
            (cosine_similarity(centroid, vectors[m]) for m in anchor.topics[0].scraps), reverse=True
        )
        k = min(member_topk, len(member_sims))
        return sum(member_sims[:k]) / k

    def find_best_two_anchors(centroid: list[float]) -> tuple[Island | None, float, float | None]:
        if not original_anchors:
            return None, -1.0, None
        scored = sorted(
            ((isl, anchor_score(centroid, isl)) for isl in original_anchors),
            key=lambda pair: -pair[1],
        )
        best_isl, best_sim = scored[0]
        second_sim = scored[1][1] if len(scored) > 1 else None
        return best_isl, best_sim, second_sim

    def attach(anchor: Island, texts: list[str]) -> None:
        # Anchor의 identity_vector/id는 그대로 둔다 - 소속 스크랩만 늘어난다
        anchor.topics[0].scraps.extend(texts)

    def record(
        texts: list[str], best_anchor: Island | None, best_sim: float, second_sim: float | None, decision: str
    ) -> None:
        if trace is None:
            return
        margin = (best_sim - second_sim) if second_sim is not None else None
        trace.append(
            AttachTrace(
                texts=list(texts),
                best_anchor_id=best_anchor.id if best_anchor is not None else None,
                best_similarity=best_sim,
                second_similarity=second_sim,
                margin=margin,
                decision=decision,
                attach_threshold=attach_threshold,
                anchor_scraps_before=list(best_anchor.topics[0].scraps) if decision == "ATTACH" else None,
            )
        )

    for label, texts in clusters.items():
        if label == -1:
            # Noise는 서로 다른 스크랩을 억지로 하나로 묶지 않는다 - 각자 독립 판단
            for text in texts:
                best_anchor, best_sim, second_sim = find_best_two_anchors(vectors[text])
                if best_anchor is not None and best_sim >= attach_threshold:
                    record([text], best_anchor, best_sim, second_sim, "ATTACH")
                    attach(best_anchor, [text])
                else:
                    record([text], best_anchor, best_sim, second_sim, "CREATE")
                    result.append(Island(next_id, vectors[text], text))
                    next_id += 1
            continue

        centroid = np.mean([vectors[t] for t in texts], axis=0).tolist()
        best_anchor, best_sim, second_sim = find_best_two_anchors(centroid)
        if best_anchor is not None and best_sim >= attach_threshold:
            record(texts, best_anchor, best_sim, second_sim, "ATTACH")
            attach(best_anchor, texts)
        else:
            record(texts, best_anchor, best_sim, second_sim, "CREATE")
            new_island = Island(next_id, centroid, texts[0])
            new_island.topics[0].scraps = list(texts)
            result.append(new_island)
            next_id += 1

    return result