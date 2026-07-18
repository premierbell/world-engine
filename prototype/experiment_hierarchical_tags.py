"""Experiment #39: Hierarchical Tag Extraction - 추상화 수준을 맞추면 Recall이
회복되는가?

Experiment #37(Tag Discriminability)의 Recall이 낮았던 이유를 Experiment
#38(Error Analysis, 정성 분석)로 들여다본 결과 - LLM이 정보를 못 뽑은 게
아니라(Case D 기각), 같은 정보를 스크랩마다 다른 추상화 수준에서 표현하고
있었다(Case B 지배적, Case A도 일부). 예: 같은 "Fine-tuning" 주제인데 한
스크랩은 `instruction_tuning`, 다른 스크랩은 `dpo`/`lora`처럼 서로 다른
하위 개념에 초점을 맞춰서 태그가 겹치지 않았다.

고정 vocabulary로 태그를 강제 정규화하는 대신(유지보수 비용이 크고, "DPO를
fine_tuning으로 뭉갠다"는 정보 손실이 있음), **2계층 태그**(LEVEL1: 넓은
상위 범주 1개, LEVEL2: 구체적 하위 개념 2~4개)를 추출해서 - 상위 계층에서는
Recall을(같은 Topic이면 LEVEL1이 겹칠 확률이 높다), 하위 계층에서는
Precision을(LEVEL2로 DPO/RLHF 같은 세부 구분을 유지) 동시에 노리는 게
이번 실험의 가설이다.

Hypothesis: 자유형 태그(flat)의 낮은 Recall은 정보 부족이 아니라 추상화
수준 불일치 때문이다. LEVEL1/LEVEL2를 함께 추출하면 Precision을 유지하면서
Recall(특히 LEVEL1 overlap)이 Experiment #37보다 뚜렷이 개선될 것이다.
"""

import json
from collections import Counter

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from experiment_anchor_model import load_virtual_user
from tag_extractor import HierarchicalTagExtractor
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


def extract_all_hierarchical_tags(
    scraps: list[dict], extractor: HierarchicalTagExtractor, cache_path: str
) -> dict[str, dict[str, list[str]]]:
    try:
        with open(cache_path) as f:
            cache: dict[str, dict[str, list[str]]] = json.load(f)
    except FileNotFoundError:
        cache = {}

    changed = False
    for s in scraps:
        if s["text"] not in cache:
            level1, level2 = extractor.extract(s["text"])
            cache[s["text"]] = {"level1": level1, "level2": level2}
            changed = True

    if changed:
        with open(cache_path, "w") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

    return cache


def candidate_levels(texts: list[str], tags_by_text: dict[str, dict[str, list[str]]]) -> tuple[set[str], set[str]]:
    l1: set[str] = set()
    l2: set[str] = set()
    for t in texts:
        l1 |= set(tags_by_text[t]["level1"])
        l2 |= set(tags_by_text[t]["level2"])
    return l1, l2


def collect_pairs(
    scraps: list[dict],
    vectors: dict[str, list[float]],
    tags_by_text: dict[str, dict[str, list[str]]],
    attach_threshold: float,
) -> tuple[list[dict], list[dict]]:
    text_to_topic = {s["text"]: s["topic"] for s in scraps}
    islands: list[Island] = []
    same: list[dict] = []
    diff: list[dict] = []

    for day in sorted({s["day"] for s in scraps}):
        day_texts = [s["text"] for s in scraps if s["day"] == day]
        if islands:
            candidates, _, _ = compute_assignment_matrix(islands, day_texts, vectors)
            topics = [dominant_topic(texts, text_to_topic) for texts in candidates]
            levels = [candidate_levels(texts, tags_by_text) for texts in candidates]
            for i in range(len(candidates)):
                for j in range(i + 1, len(candidates)):
                    l1_i, l2_i = levels[i]
                    l1_j, l2_j = levels[j]
                    record = {
                        "level1_overlap": 1.0 if (l1_i & l1_j) else 0.0,
                        "level1_jaccard": jaccard(l1_i, l1_j),
                        "level2_jaccard": jaccard(l2_i, l2_j),
                    }
                    (same if topics[i] == topics[j] else diff).append(record)
        islands = night_batch_anchor(islands, day_texts, vectors, attach_threshold=attach_threshold)

    return same, diff


def print_summary(user_name: str, same: list[dict], diff: list[dict]) -> None:
    table = Table(title=f"Experiment #39: Hierarchical Tag 신호 요약 ({user_name})")
    for col in ("지표", "같은 주제 mean", "다른 주제 mean", "차이(같은-다른)"):
        table.add_column(col)

    for key, label in (
        ("level1_overlap", "LEVEL1 최소 1개 겹침 비율"),
        ("level1_jaccard", "LEVEL1 Jaccard"),
        ("level2_jaccard", "LEVEL2 Jaccard"),
    ):
        s_vals = [r[key] for r in same]
        d_vals = [r[key] for r in diff]
        s_mean = sum(s_vals) / len(s_vals) if s_vals else float("nan")
        d_mean = sum(d_vals) / len(d_vals) if d_vals else float("nan")
        table.add_row(label, f"{s_mean:.3f}", f"{d_mean:.3f}", f"{s_mean - d_mean:+.3f}")

    console.print(table)

    # combined rule: LEVEL1 공유 + LEVEL2 Jaccard > 0 -> "같은 주제로 추정"
    def combined_positive(r: dict) -> bool:
        return r["level1_overlap"] > 0

    same_hit = sum(1 for r in same if combined_positive(r))
    diff_hit = sum(1 for r in diff if combined_positive(r))
    precision = same_hit / (same_hit + diff_hit) if (same_hit + diff_hit) else float("nan")
    recall = same_hit / len(same) if same else float("nan")
    console.print(
        f"  [bold]LEVEL1 overlap>=1 규칙: recall={recall:.1%}({same_hit}/{len(same)}), "
        f"precision={precision:.1%}({same_hit}/{same_hit+diff_hit})[/bold]\n"
    )


def main() -> None:
    load_dotenv()
    config = load_config()
    embedding_provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])
    tag_extractor = HierarchicalTagExtractor(model=config["label"]["model"])

    for user_name, path, cache_path in (
        ("Backend User", "../experiments/virtual_users/backend_developer.json", "backend_developer_hierarchical_tags.json"),
        ("AI Researcher", "../experiments/virtual_users/ai_researcher.json", "ai_researcher_hierarchical_tags.json"),
    ):
        user = load_virtual_user(path)
        scraps = user["scraps"]
        vectors = {s["text"]: embedding_provider.embed(s["text"]) for s in scraps}
        tags_by_text = extract_all_hierarchical_tags(scraps, tag_extractor, cache_path)

        same, diff = collect_pairs(scraps, vectors, tags_by_text, attach_threshold=0.30)
        print_summary(user_name, same, diff)


if __name__ == "__main__":
    main()
