"""Experiment #40: Tag Relation Analysis (그래프 관찰, 임베딩/LLM/알고리즘 판단 없음).

Research Question #6("Topic Identity는 개별 문서의 속성인가, 여러 문서에
걸친 관계적 속성인가?") 첫 실험. Finding #009까지의 모든 시도(문서 임베딩,
문서 태그, 계층 태그)는 전부 암묵적으로 "Identity는 개별 객체(문서 하나,
또는 그 문서가 낸 태그 하나) 안에 있다"고 가정했다. RQ#6은 그 전제 자체를
의심한다.

바로 태그를 임베딩하고 HDBSCAN으로 묶는 대신(Finding #008의 실패를 태그
레벨에서 반복할 위험이 있음 - "결국 다시 cosine similarity"), 더 앞선
질문부터 순수 관찰로 확인한다: **태그들 사이에 실제로 안정적인 관계
구조(connectivity)가 존재하는가?**

Experiment #37에서 이미 추출한 freeform 태그(embedding도 LLM도 추가로
쓰지 않음)로 그래프를 만든다 - 노드는 태그, 엣지는 "같은 스크랩에
함께 등장했다"(co-occurrence). 이 그래프의 **Connected Component**가
실제 Topic 경계와 얼마나 일치하는지만 본다. HDBSCAN도, embedding도,
새 LLM 판단도 없다 - 순수하게 "이미 있는 관계 정보만으로 뭔가 보이는가"
를 확인하는 관찰 실험이다.
"""

import json
from collections import Counter, defaultdict

from rich.console import Console
from rich.table import Table

from experiment_anchor_model import load_virtual_user

console = Console()


class UnionFind:
    def __init__(self, items: list[str]):
        self.parent = {item: item for item in items}

    def find(self, x: str) -> str:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def build_tag_graph(scraps: list[dict], tags_by_text: dict[str, list[str]]) -> tuple[UnionFind, Counter, dict]:
    all_tags = {tag for tags in tags_by_text.values() for tag in tags}
    uf = UnionFind(list(all_tags))
    degree: Counter = Counter()
    edge_weight: dict[tuple[str, str], int] = defaultdict(int)

    for s in scraps:
        tags = tags_by_text[s["text"]]
        for i in range(len(tags)):
            for j in range(i + 1, len(tags)):
                a, b = sorted((tags[i], tags[j]))
                if a != b:
                    edge_weight[(a, b)] += 1
                    uf.union(a, b)
        for t in tags:
            degree[t] += len(tags) - 1  # 같은 스크랩 내 다른 태그 수만큼 연결

    return uf, degree, edge_weight


def analyze(user_name: str, scraps: list[dict], tags_by_text: dict[str, list[str]]) -> None:
    text_to_topic = {s["text"]: s["topic"] for s in scraps}
    uf, degree, edge_weight = build_tag_graph(scraps, tags_by_text)

    all_tags = list(uf.parent.keys())
    components: dict[str, list[str]] = defaultdict(list)
    for tag in all_tags:
        components[uf.find(tag)].append(tag)

    isolated = sum(1 for t in all_tags if degree[t] == 0)
    console.print(
        f"[bold]{user_name}: 전체 태그 {len(all_tags)}개, 고유 엣지 {len(edge_weight)}개, "
        f"고립 노드(다른 태그와 한 번도 안 엮인 태그) {isolated}개[/bold]"
    )
    console.print(f"  Connected Component 수: {len(components)}, 최대 크기: {max(len(v) for v in components.values())}")

    # 각 real Topic의 태그가 몇 개의 Component에 흩어져 있는지 (Duplication과 유사한 지표)
    topic_to_components: dict[str, set[str]] = defaultdict(set)
    for s in scraps:
        topic = s["topic"]
        for tag in tags_by_text[s["text"]]:
            topic_to_components[topic].add(uf.find(tag))

    table = Table(title=f"Experiment #40: 실제 Topic별 태그가 흩어진 Component 수 ({user_name})")
    table.add_column("실제 Topic")
    table.add_column("태그가 걸친 Component 수")
    for topic, comps in sorted(topic_to_components.items(), key=lambda kv: -len(kv[1])):
        table.add_row(topic, str(len(comps)))
    console.print(table)

    # 각 Component가 몇 개의 서로 다른 real Topic에 걸쳐 있는지 (Purity와 유사한 지표) - 크기 2 이상만
    component_to_topics: dict[str, Counter] = defaultdict(Counter)
    for s in scraps:
        for tag in tags_by_text[s["text"]]:
            component_to_topics[uf.find(tag)][s["topic"]] += 1

    big_components = {root: topics for root, topics in component_to_topics.items() if len(components[root]) >= 3}
    table2 = Table(title=f"Experiment #40: 크기 3 이상 Component의 Topic 구성 ({user_name})")
    for col in ("Component 크기(태그 수)", "관련 실제 Topic 구성"):
        table2.add_column(col)
    for root, topics in sorted(big_components.items(), key=lambda kv: -len(components[kv[0]])):
        composition = ", ".join(f"{topic}x{n}" for topic, n in topics.most_common())
        table2.add_row(str(len(components[root])), composition)
    console.print(table2)
    console.print()


def main() -> None:
    for user_name, path, cache_path in (
        ("Backend User", "../experiments/virtual_users/backend_developer.json", "backend_developer_tags.json"),
        ("AI Researcher", "../experiments/virtual_users/ai_researcher.json", "ai_researcher_tags.json"),
    ):
        user = load_virtual_user(path)
        scraps = user["scraps"]
        with open(cache_path) as f:
            tags_by_text = json.load(f)

        analyze(user_name, scraps, tags_by_text)


if __name__ == "__main__":
    main()
