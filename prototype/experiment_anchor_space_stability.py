"""Experiment #42: Anchor Space Stability Analysis.

Experiment #41이 예상 밖으로 드러낸 교란 요인 - Day7과 Day30 관측은 같은
Anchor 집합을 두 번 본 게 아니라 서로 다른(진화한) Anchor 집합을 봤다 -
을 직접 측정한다. "GPS 위성이 계속 움직이는데 자동차 위치가 흔들린다고
말하는 것과 같다"(H0): Candidate의 Confidence 축적(H2, Research Question
#7)을 논하려면, 먼저 그 기준이 되는 Anchor Space 자체가 안정화되는지부터
확인해야 한다.

이 실험은 판단 로직을 바꾸지 않는다 - night_batch_anchor()가 이미 남기는
AttachTrace(ATTACH vs CREATE 결정)를 그대로 읽어서, 배치마다 Anchor
Space가 얼마나 늘어나는지(창조율)와 기존 Anchor로 흡수되는 비율만
집계한다.

주의: Anchor의 identity_vector는 설계상 절대 불변이다(Anchor Model
Immutability). 그래서 "Anchor 이동량"은 이 v0 구현에서는 항상 0이다 -
이번 실험이 측정할 수 있는 건 "Anchor 개수 자체가 늘어나는 속도"뿐이고,
"기존 Anchor가 옮겨가는 정도"는 애초에 측정 대상이 아니다(이 사실 자체가
Insight의 일부다).
"""

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


def run_persona(user_name: str, scraps: list[dict], vectors: dict[str, list[float]], attach_threshold: float) -> None:
    days = sorted({s["day"] for s in scraps})
    islands: list[Island] = []

    table = Table(title=f"Experiment #42: Anchor Space Stability ({user_name})")
    for col in ("Day", "새 스크랩", "배치 전 Anchor 수", "배치 후 Anchor 수", "신규 Anchor", "기존에 흡수", "신규 생성률"):
        table.add_column(col)

    for day in days:
        day_texts = [s["text"] for s in scraps if s["day"] == day]
        n_before = len(islands)
        trace: list[AttachTrace] = []
        islands = night_batch_anchor(islands, day_texts, vectors, attach_threshold=attach_threshold, trace=trace)
        n_after = len(islands)

        n_created = sum(1 for t in trace if t.decision == "CREATE")
        n_attached = sum(1 for t in trace if t.decision == "ATTACH")
        total_decisions = n_created + n_attached
        creation_rate = n_created / total_decisions if total_decisions else float("nan")

        table.add_row(
            str(day), str(len(day_texts)), str(n_before), str(n_after),
            str(n_created), str(n_attached),
            f"{creation_rate:.1%}" if total_decisions else "-",
        )

    console.print(table)
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

        run_persona(user_name, scraps, vectors, attach_threshold=0.30)


if __name__ == "__main__":
    main()
