"""Experiment #37: Tag Discriminability Analysis.

Research Question #5("Similarity만으로 Topic Identity를 만들 수 있는가?") 첫
실험. Finding #008까지 실패한 신호(Margin/Representation/Direct Similarity/
구조적 신호)는 전부 같은 정보원(embedding → cosine similarity → 숫자 하나)
에서 파생됐다 - 판단 규칙만 바뀌었지 정보 자체는 한 번도 바뀌지 않았다.

이번엔 완전히 다른 정보원을 시도한다: AI가 스크랩마다 구조화된 키워드
태그를 추출하고(`tag_extractor.py`, ai_rules.md Rule 1과 충돌하지 않음 -
태그 추출도 "이해" 계층이지 "판단" 계층이 아니다), 두 candidate의 태그
집합이 얼마나 겹치는지(Jaccard)를 새로운 신호로 써본다.

**이 실험은 아직 attach 판단을 바꾸지 않는다.** Experiment #31의 교훈
(post-hoc 신호가 좋아 보여도 실제 decision policy로 쓰면 다른 결과가
나올 수 있다)을 반영해서, 이번엔 순서를 바꾼다 - 먼저 신호 자체의
판별력만 Experiment #35와 같은 방법론(같은 실제 주제 쌍 vs 다른 실제
주제 쌍의 분포 비교)으로 검증하고, 판별력이 확인된 뒤에만 실제 attach
메커니즘에 적용하는 걸 고려한다(Experiment #38, 미실행).
"""

import json
from collections import Counter

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from experiment_anchor_model import load_virtual_user
from tag_extractor import OpenAITagExtractor
from world import Island, compute_assignment_matrix, night_batch_anchor

console = Console()


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def dominant_topic(texts: list[str], text_to_topic: dict[str, str]) -> str:
    return Counter(text_to_topic[t] for t in texts).most_common(1)[0][0]


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def extract_all_tags(scraps: list[dict], tag_extractor: OpenAITagExtractor, cache_path: str) -> dict[str, list[str]]:
    """반복 실행 비용을 줄이기 위해 텍스트->태그 매핑을 로컬에 캐싱한다."""
    try:
        with open(cache_path) as f:
            cache: dict[str, list[str]] = json.load(f)
    except FileNotFoundError:
        cache = {}

    changed = False
    for s in scraps:
        if s["text"] not in cache:
            cache[s["text"]] = tag_extractor.extract(s["text"])
            changed = True

    if changed:
        with open(cache_path, "w") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

    return cache


def candidate_tags(texts: list[str], tags_by_text: dict[str, list[str]]) -> set[str]:
    result: set[str] = set()
    for t in texts:
        result |= set(tags_by_text[t])
    return result


def collect_pairs(
    scraps: list[dict], vectors: dict[str, list[float]], tags_by_text: dict[str, list[str]], attach_threshold: float
) -> tuple[list[float], list[float]]:
    text_to_topic = {s["text"]: s["topic"] for s in scraps}
    islands: list[Island] = []
    same_overlaps: list[float] = []
    diff_overlaps: list[float] = []

    for day in sorted({s["day"] for s in scraps}):
        day_texts = [s["text"] for s in scraps if s["day"] == day]
        if islands:
            candidates, _, _ = compute_assignment_matrix(islands, day_texts, vectors)
            topics = [dominant_topic(texts, text_to_topic) for texts in candidates]
            tags = [candidate_tags(texts, tags_by_text) for texts in candidates]
            for i in range(len(candidates)):
                for j in range(i + 1, len(candidates)):
                    overlap = jaccard(tags[i], tags[j])
                    if topics[i] == topics[j]:
                        same_overlaps.append(overlap)
                    else:
                        diff_overlaps.append(overlap)
        islands = night_batch_anchor(islands, day_texts, vectors, attach_threshold=attach_threshold)

    return same_overlaps, diff_overlaps


def print_comparison(user_name: str, same: list[float], diff: list[float]) -> None:
    table = Table(title=f"Experiment #37: Tag Jaccard Overlap 분포 ({user_name})")
    for col in ("구간", "같은 실제 주제 쌍", "다른 실제 주제 쌍"):
        table.add_column(col)

    bins = [(0.0, 0.001), (0.001, 0.15), (0.15, 0.3), (0.3, 0.45), (0.45, 0.6), (0.6, 0.8), (0.8, 1.001)]
    for lo, hi in bins:
        same_n = sum(1 for s in same if lo <= s < hi)
        diff_n = sum(1 for s in diff if lo <= s < hi)
        table.add_row(f"[{lo:.2f}, {hi:.2f})", str(same_n), str(diff_n))

    console.print(table)
    if same:
        console.print(f"  같은 주제 쌍: n={len(same)}, mean={sum(same)/len(same):.3f}")
    if diff:
        console.print(f"  다른 주제 쌍: n={len(diff)}, mean={sum(diff)/len(diff):.3f}")
    if same and diff:
        console.print(f"  [bold]차이(같은-다른): {sum(same)/len(same) - sum(diff)/len(diff):+.3f}[/bold]")
    console.print()


def main() -> None:
    load_dotenv()
    config = load_config()
    embedding_provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])
    tag_extractor = OpenAITagExtractor(model=config["label"]["model"])

    for user_name, path, cache_path in (
        ("Backend User", "../experiments/virtual_users/backend_developer.json", "backend_developer_tags.json"),
        ("AI Researcher", "../experiments/virtual_users/ai_researcher.json", "ai_researcher_tags.json"),
    ):
        user = load_virtual_user(path)
        scraps = user["scraps"]
        vectors = {s["text"]: embedding_provider.embed(s["text"]) for s in scraps}
        tags_by_text = extract_all_tags(scraps, tag_extractor, cache_path)

        same, diff = collect_pairs(scraps, vectors, tags_by_text, attach_threshold=0.30)
        print_comparison(user_name, same, diff)


if __name__ == "__main__":
    main()
