"""Experiment #17: Semantic Factor Probe.

Experiment #16(Register Control)은 "register만으로는 설명되지 않는다"까지만
증명했다 — Sports-Finance가 실제로 무엇을 공유하는지는 여전히 미검증
Hypothesis였다(`docs/algorithm_limitations.md` Finding #002 Root Cause 참고).
후보는 경쟁(competition)/순위(rank)/예측(prediction)/통계(statistics)/
시장분석(market analysis)/시즌성(time-series) 6가지였다.

이 실험은 각 후보를 스포츠도 금융도 아닌 완전히 도메인 중립적인 문장(probe)으로
표현한 뒤, `golden_dataset/semantic_atlas/dataset.json`의 8개 도메인 centroid와
비교한다. 어떤 probe가 Sports와 Finance에는 특이적으로 가깝고 다른 6개 도메인
(Backend/AI/Cloud/Database/Security/Science)과는 안 가깝다면, 그 factor가
Sports-Finance 근접성의 실제 원인일 가능성이 커진다.
"""

import json
from collections import defaultdict

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from similarity import cosine_similarity

console = Console()

ATLAS_DATASET_PATH = "../golden_dataset/semantic_atlas/dataset.json"

PROBES = {
    "경쟁(Competition)": "여러 참가자가 서로의 성과를 비교하며 우위를 다툰다.",
    "순위(Rank)": "정기적으로 갱신되는 순위표에서 상위권과 하위권의 격차를 확인한다.",
    "예측(Prediction)": "현재까지 나온 데이터를 바탕으로 앞으로의 결과를 전망한다.",
    "통계(Statistics)": "수치 데이터를 집계하고 평균이나 분산 같은 지표로 요약한다.",
    "시장분석(Market Analysis)": "여러 참여자의 움직임을 분석해 전체 흐름의 강약을 판단한다.",
    "시즌성(Time-series)": "일정한 주기로 반복되는 패턴을 시간 순서대로 추적한다.",
}


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_dataset(path: str) -> dict[str, dict]:
    with open(path) as f:
        return json.load(f)


def centroid(vectors: list[list[float]]) -> list[float]:
    n = len(vectors)
    dim = len(vectors[0])
    return [sum(v[i] for v in vectors) / n for i in range(dim)]


def main() -> None:
    load_dotenv()
    config = load_config()
    provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])

    dataset = load_dataset(ATLAS_DATASET_PATH)
    items = list(dataset.items())
    atlas_vectors = {key: provider.embed(entry["text"]) for key, entry in items}

    vectors_by_island: dict[str, list[list[float]]] = defaultdict(list)
    for key, entry in items:
        vectors_by_island[entry["island"]].append(atlas_vectors[key])

    islands = sorted(vectors_by_island.keys())
    island_centroids = {isl: centroid(vecs) for isl, vecs in vectors_by_island.items()}

    probe_vectors = {name: provider.embed(text) for name, text in PROBES.items()}

    detail_table = Table(title="Experiment #17: Probe x Island Centroid Cosine Similarity")
    detail_table.add_column("Probe")
    for isl in islands:
        detail_table.add_column(isl)
    for name in PROBES:
        row = [name]
        for isl in islands:
            sim = cosine_similarity(probe_vectors[name], island_centroids[isl])
            row.append(f"{sim:.3f}")
        detail_table.add_row(*row)
    console.print(detail_table)

    other_islands = [isl for isl in islands if isl not in ("Sports", "Finance")]

    summary_table = Table(title="Experiment #17: Sports+Finance Specificity Ranking")
    for col in ("Probe", "Sports", "Finance", "min(Sports,Finance)", "max(다른 6개)", "Specificity Gap"):
        summary_table.add_column(col)

    rows = []
    for name in PROBES:
        sim_sports = cosine_similarity(probe_vectors[name], island_centroids["Sports"])
        sim_finance = cosine_similarity(probe_vectors[name], island_centroids["Finance"])
        sim_others = [cosine_similarity(probe_vectors[name], island_centroids[isl]) for isl in other_islands]
        min_target = min(sim_sports, sim_finance)
        max_other = max(sim_others)
        gap = min_target - max_other
        rows.append((name, sim_sports, sim_finance, min_target, max_other, gap))

    rows.sort(key=lambda r: -r[5])
    for name, sim_sports, sim_finance, min_target, max_other, gap in rows:
        summary_table.add_row(
            name, f"{sim_sports:.3f}", f"{sim_finance:.3f}", f"{min_target:.3f}", f"{max_other:.3f}", f"{gap:+.3f}"
        )

    console.print(summary_table)
    console.print(
        "\n[bold]Specificity Gap > 0 이면 이 probe가 Sports+Finance 둘 다에게, "
        "다른 어떤 도메인보다도 특이적으로 가깝다는 뜻[/bold]"
    )


if __name__ == "__main__":
    main()
