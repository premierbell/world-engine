"""Experiment #38: Tag Overlap Error Analysis (정성 분석, 알고리즘 없음).

Experiment #37에서 태그 Jaccard overlap이 거의 항상 0에 가까웠던 이유를
사람이 직접 눈으로 분류한다 - "태그가 신호로서 나쁘다"는 결론을 바로
내리지 않고, 원인을 먼저 분리한다:

- Synonym: 같은 개념인데 표현(문자열)만 다름 (예: self_attention vs attention)
- Abstraction: 추상화 수준이 달라서 안 겹침 (예: transformer vs positional_encoding)
- Extraction instability: 추출 자체가 불안정(언어 혼용, 형식 불일치 등 -
  프롬프트가 "영어 소문자 snake_case"를 명시했는데도 한국어/공백이 섞임)
- Genuine difference: 실제로 공유할 태그가 없음(같은 주제라도 하위 개념이 정말 다름)

이 스크립트는 판단을 자동화하지 않는다 - 같은 실제 주제 쌍/다른 실제
주제 쌍 표본을 뽑아서 태그를 나란히 출력하기만 한다. 분류는 사람이
읽고 기록한다(Decision에 반영).
"""

import json
import random
from collections import Counter

from rich.console import Console
from rich.table import Table

from experiment_anchor_model import load_virtual_user
from world import Island, compute_assignment_matrix, night_batch_anchor

console = Console()


def dominant_topic(texts: list[str], text_to_topic: dict[str, str]) -> str:
    return Counter(text_to_topic[t] for t in texts).most_common(1)[0][0]


def collect_candidate_pairs_with_tags(
    scraps: list[dict], vectors: dict[str, list[float]], tags_by_text: dict[str, list[str]], attach_threshold: float
) -> list[dict]:
    text_to_topic = {s["text"]: s["topic"] for s in scraps}
    islands: list[Island] = []
    pairs = []

    for day in sorted({s["day"] for s in scraps}):
        day_texts = [s["text"] for s in scraps if s["day"] == day]
        if islands:
            candidates, _, _ = compute_assignment_matrix(islands, day_texts, vectors)
            topics = [dominant_topic(texts, text_to_topic) for texts in candidates]
            for i in range(len(candidates)):
                for j in range(i + 1, len(candidates)):
                    tags_i = sorted({t for text in candidates[i] for t in tags_by_text[text]})
                    tags_j = sorted({t for text in candidates[j] for t in tags_by_text[text]})
                    pairs.append(
                        {
                            "same_topic": topics[i] == topics[j],
                            "topic_i": topics[i],
                            "topic_j": topics[j],
                            "tags_i": tags_i,
                            "tags_j": tags_j,
                            "overlap": sorted(set(tags_i) & set(tags_j)),
                        }
                    )
        islands = night_batch_anchor(islands, day_texts, vectors, attach_threshold=attach_threshold)

    return pairs


def print_sample(user_name: str, pairs: list[dict], n_each: int, seed: int) -> None:
    same_pairs = [p for p in pairs if p["same_topic"]]
    diff_pairs = [p for p in pairs if not p["same_topic"]]
    rng = random.Random(seed)
    sample = rng.sample(same_pairs, min(n_each, len(same_pairs))) + rng.sample(diff_pairs, min(n_each, len(diff_pairs)))

    table = Table(title=f"Experiment #38: Tag Overlap Error Analysis 표본 ({user_name})")
    for col in ("같은주제?", "Topic A / B", "Tags A", "Tags B", "겹침"):
        table.add_column(col)

    for p in sample:
        table.add_row(
            "O" if p["same_topic"] else "X",
            f"{p['topic_i']} / {p['topic_j']}",
            ", ".join(p["tags_i"]),
            ", ".join(p["tags_j"]),
            ", ".join(p["overlap"]) if p["overlap"] else "-",
        )

    console.print(table)
    console.print()


def main() -> None:
    for user_name, path, cache_path in (
        ("AI Researcher", "../experiments/virtual_users/ai_researcher.json", "ai_researcher_tags.json"),
        ("Backend User", "../experiments/virtual_users/backend_developer.json", "backend_developer_tags.json"),
    ):
        user = load_virtual_user(path)
        scraps = user["scraps"]
        with open(cache_path) as f:
            tags_by_text = json.load(f)

        import yaml
        from dotenv import load_dotenv

        from embedding_provider import OpenAIEmbeddingProvider

        load_dotenv()
        with open("config.yaml") as f:
            config = yaml.safe_load(f)
        embedding_provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])
        vectors = {s["text"]: embedding_provider.embed(s["text"]) for s in scraps}

        pairs = collect_candidate_pairs_with_tags(scraps, vectors, tags_by_text, attach_threshold=0.30)
        print_sample(user_name, pairs, n_each=10, seed=1)


if __name__ == "__main__":
    main()
