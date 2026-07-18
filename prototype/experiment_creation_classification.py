"""Experiment #43: Anchor Creation Classification - Novel Expansion vs Redundant Split.

Experiment #42는 "Anchor Creation Rate"를 측정했지만, 사용자가 지적한 대로
이건 Anchor Space Stability의 충분한 proxy가 아니다 - 새 Anchor가 생기는
이유가 (a) 진짜 새로운 관심사(Novel Expansion, 정상 성장)인지 (b) 이미
있는 Anchor와 충분히 비슷했는데도 붙지 못해 쪼개진 것(Redundant Split,
회피 가능한 파편화)인지를 구분하지 못하면, "창조율이 높다"는 사실만으로는
아무것도 판단할 수 없다.

night_batch_anchor()가 이미 매 CREATE 결정마다 "가장 가까웠던 기존
Anchor"와 그 유사도(best_similarity)를 AttachTrace에 남긴다(이번 실험을
위해 CREATE 케이스에도 anchor_scraps_before를 채우도록 world.py를 확장 -
판단 로직 자체는 안 바꿈, 진단 정보만 추가). 이 실험은 ground truth로
(offline 진단 목적, Experiment #29/#35와 같은 성격) 각 CREATE 이벤트를
분류한다:

- **Novel Expansion**: 새로 생긴 Anchor의 실제 주제가, 가장 가까웠던 기존
  Anchor의 실제 주제와 다르다 - 정상적인 성장.
- **Redundant Split**: 새로 생긴 Anchor의 실제 주제가, 가장 가까웠던 기존
  Anchor의 실제 주제와 같다 - 붙었어야 했는데 못 붙은 회피 가능한 파편화.

Experiment #42의 "창조율 45.5%(Backend)/28.6%(AI Researcher)"가 실제로는
Novel Expansion 위주인지 Redundant Split 위주인지가 이번 실험의 핵심
질문이다.
"""

from collections import Counter

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from experiment_anchor_model import load_virtual_user
from world import AttachTrace, Island, night_batch_anchor

console = Console()


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def dominant_topic(texts: list[str], text_to_topic: dict[str, str]) -> str:
    return Counter(text_to_topic[t] for t in texts).most_common(1)[0][0]


def classify_creations(
    scraps: list[dict], vectors: dict[str, list[float]], attach_threshold: float
) -> list[dict]:
    text_to_topic = {s["text"]: s["topic"] for s in scraps}
    islands: list[Island] = []
    records = []

    for day in sorted({s["day"] for s in scraps}):
        day_texts = [s["text"] for s in scraps if s["day"] == day]
        trace: list[AttachTrace] = []
        islands = night_batch_anchor(islands, day_texts, vectors, attach_threshold=attach_threshold, trace=trace)
        for event in trace:
            if event.decision != "CREATE":
                continue
            new_topic = dominant_topic(event.texts, text_to_topic)
            if event.anchor_scraps_before is None:
                # 비교 대상 Anchor가 아예 없던 최초 배치 - Novel로 취급(비교 불가)
                nearest_topic = None
                classification = "Novel Expansion (첫 Anchor)"
            else:
                nearest_topic = dominant_topic(event.anchor_scraps_before, text_to_topic)
                classification = "Redundant Split" if nearest_topic == new_topic else "Novel Expansion"
            records.append(
                {
                    "day": day,
                    "size": len(event.texts),
                    "new_topic": new_topic,
                    "nearest_existing_topic": nearest_topic,
                    "best_similarity": event.best_similarity,
                    "classification": classification,
                }
            )

    return records


def print_summary(user_name: str, records: list[dict]) -> None:
    counts = Counter(r["classification"] for r in records)
    table = Table(title=f"Experiment #43: CREATE 이벤트 분류 요약 ({user_name})")
    for col in ("분류", "건수", "비율"):
        table.add_column(col)
    total = len(records)
    for label, n in counts.most_common():
        table.add_row(label, str(n), f"{n/total:.1%}" if total else "-")
    console.print(table)

    redundant = [r for r in records if r["classification"] == "Redundant Split"]
    if redundant:
        detail = Table(title=f"Experiment #43: Redundant Split 상세 ({user_name})")
        for col in ("Day", "크기", "새 Anchor 주제", "가장 가까운 기존 Anchor 주제", "best_similarity"):
            detail.add_column(col)
        for r in redundant:
            detail.add_row(
                str(r["day"]), str(r["size"]), r["new_topic"], r["nearest_existing_topic"],
                f"{r['best_similarity']:.3f}",
            )
        console.print(detail)
    console.print()


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

        records = classify_creations(scraps, vectors, attach_threshold=0.30)
        print_summary(user_name, records)


if __name__ == "__main__":
    main()
