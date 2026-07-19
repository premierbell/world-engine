"""Experiment #52: RQ10-0 (Ontology of Semantic Resolution) - Stage A/B.

docs/research_phase_2_rq10-0.md에서 정의한 첫 실험이다. 새 LLM 호출 없이
기존 캐시(Experiment #47의 mechanism_cache, #50의 topic_cache)와, embedding만
새로 한 번(36개, O(n) - pairwise가 아니므로 저렴) 계산해서 재사용한다.

Stage A. Measurement Invariance
    같은 데이터를 embedding cosine / LLM Mechanism 프롬프트 / LLM Topic
    프롬프트, 세 가지 다른 도구로 봤을 때 같은 구조가 보이는가?
    - Odd-one-out agreement (국소 구조)
    - Distance matrix rank correlation, Kendall's tau (전역 구조)

Stage B. Latent Geometry
    Stage A에서 공통 구조가 확인된 뒤에만 의미가 있다. 각 modality가
    Tree(H1)에 가까운지 Metric(H2)에 가까운지를 본다.
    - Ultrametric violation rate
    - Cophenetic correlation (average-linkage, ward-linkage 둘 다)
    - MDS stress (2D)

7140개 triple은 독립 표본이 아니므로(같은 점이 여러 triple에 반복 등장)
p-value가 아니라 효과크기(비율, 상관계수) 위주로 본다.
"""

import itertools
import json

import numpy as np
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from scipy.cluster.hierarchy import cophenet, linkage
from scipy.spatial.distance import squareform
from scipy.stats import kendalltau
from sklearn.manifold import MDS

from embedding_provider import OpenAIEmbeddingProvider
from experiment_anchor_model import load_virtual_user
from experiment_pairwise_granularity import curated_sample, load_config

console = Console()

MECHANISM_CACHE_PATH = "pairwise_judgment_cache.json"
TOPIC_CACHE_PATH = "pairwise_judgment_topic_cache.json"
EMBEDDING_CACHE_PATH = "resolution_ontology_embedding_cache.json"


def pair_key(text_a: str, text_b: str) -> str:
    a, b = sorted((text_a, text_b))
    return f"{a}|||{b}"


def load_cache(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_cache(path: str, cache: dict) -> None:
    with open(path, "w") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def build_score_matrix(texts: list[str], pair_scores: dict[str, float]) -> np.ndarray:
    n = len(texts)
    m = np.ones((n, n))
    for i, j in itertools.combinations(range(n), 2):
        score = pair_scores[pair_key(texts[i], texts[j])]
        m[i, j] = m[j, i] = score
    return m


def similarity_to_distance(sim: np.ndarray) -> np.ndarray:
    d = 1.0 - sim
    np.fill_diagonal(d, 0.0)
    return d


def odd_one_out(sim_row: tuple[float, float, float]) -> int:
    """세 쌍의 유사도(AB, AC, BC)에서 odd-one-out(가장 먼 점)의 인덱스를 반환한다."""
    ab, ac, bc = sim_row
    # 가장 유사도가 낮은 쌍의 상대 인덱스가 곧 "가장 가까운 쌍에 안 낀 점"과 무관하므로
    # 대신 가장 유사도가 "높은" 쌍을 찾고, 거기 안 낀 점을 odd-one-out으로 본다.
    pairs = {"AB": ab, "AC": ac, "BC": bc}
    closest_pair = max(pairs, key=pairs.get)
    return {"AB": 2, "AC": 1, "BC": 0}[closest_pair]  # 안 낀 점의 인덱스(0=A,1=B,2=C)


def stage_a_measurement_invariance(
    texts: list[str], sim_matrices: dict[str, np.ndarray]
) -> None:
    console.rule("[bold]Stage A: Measurement Invariance[/bold]")
    n = len(texts)
    modalities = list(sim_matrices.keys())

    ooo: dict[str, list[int]] = {m: [] for m in modalities}
    for i, j, k in itertools.combinations(range(n), 3):
        for m in modalities:
            s = sim_matrices[m]
            ooo[m].append(odd_one_out((s[i, j], s[i, k], s[j, k])))

    agree_table = Table(title="Odd-one-out agreement (local structure)")
    agree_table.add_column("Modality Pair")
    agree_table.add_column("Agreement")
    n_triples = len(ooo[modalities[0]])
    for m1, m2 in itertools.combinations(modalities, 2):
        agree = sum(1 for a, b in zip(ooo[m1], ooo[m2]) if a == b) / n_triples
        agree_table.add_row(f"{m1} vs {m2}", f"{agree:.1%}")
    console.print(agree_table)
    console.print(f"[dim]우연 수준(무작위 3지선다) = 33.3%, n_triples={n_triples}[/dim]\n")

    corr_table = Table(title="Distance matrix rank correlation (global structure, Kendall's tau)")
    corr_table.add_column("Modality Pair")
    corr_table.add_column("Kendall's tau")
    iu = np.triu_indices(n, k=1)
    for m1, m2 in itertools.combinations(modalities, 2):
        tau, _ = kendalltau(sim_matrices[m1][iu], sim_matrices[m2][iu])
        corr_table.add_row(f"{m1} vs {m2}", f"{tau:.3f}")
    console.print(corr_table)


def stage_b_latent_geometry(texts: list[str], sim_matrices: dict[str, np.ndarray]) -> None:
    console.rule("[bold]Stage B: Latent Geometry (Tree vs Metric)[/bold]")
    n = len(texts)

    table = Table(title="Tree(H1) vs Metric(H2) fit per modality")
    for col in (
        "Modality",
        "Ultrametric violation rate",
        "Cophenetic corr (average)",
        "Cophenetic corr (ward)",
        "MDS stress (2D)",
    ):
        table.add_column(col)

    for name, sim in sim_matrices.items():
        dist = similarity_to_distance(sim)
        condensed = squareform(dist, checks=False)

        violations = 0
        total = 0
        for i, j, k in itertools.combinations(range(n), 3):
            d_ij, d_ik, d_jk = dist[i, j], dist[i, k], dist[j, k]
            largest_two = sorted([d_ij, d_ik, d_jk])[1:]
            if abs(largest_two[0] - largest_two[1]) > 0.05 * max(largest_two):
                violations += 1
            total += 1
        violation_rate = violations / total

        cophenetic_scores = {}
        for method in ("average", "ward"):
            Z = linkage(condensed, method=method)
            corr, _coph_dists = cophenet(Z, condensed)
            cophenetic_scores[method] = corr

        mds = MDS(n_components=2, dissimilarity="precomputed", random_state=7, normalized_stress="auto")
        mds.fit(dist)
        stress = mds.stress_

        table.add_row(
            name,
            f"{violation_rate:.1%}",
            f"{cophenetic_scores['average']:.3f}",
            f"{cophenetic_scores['ward']:.3f}",
            f"{stress:.3f}",
        )

    console.print(table)


def main() -> None:
    load_dotenv()
    config = load_config()

    user = load_virtual_user("../experiments/virtual_users/ai_researcher.json")
    from experiment_pairwise_granularity import MECHANISM_LABELS

    all_scraps = [s for s in user["scraps"] if s["text"] in MECHANISM_LABELS]
    scraps = curated_sample(all_scraps, per_topic_cap=4)
    texts = [s["text"] for s in scraps]
    console.print(f"[bold]표본 {len(texts)}개 (Experiment #47/#50과 동일)[/bold]\n")

    mechanism_cache = load_cache(MECHANISM_CACHE_PATH)
    topic_cache = load_cache(TOPIC_CACHE_PATH)
    embedding_cache = load_cache(EMBEDDING_CACHE_PATH)

    provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])
    for t in texts:
        if t not in embedding_cache:
            embedding_cache[t] = provider.embed(t)
    save_cache(EMBEDDING_CACHE_PATH, embedding_cache)

    vectors = np.array([embedding_cache[t] for t in texts])
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    unit = vectors / norms
    embed_sim = unit @ unit.T
    np.fill_diagonal(embed_sim, 1.0)

    mechanism_sim = build_score_matrix(texts, mechanism_cache)
    topic_sim = build_score_matrix(texts, topic_cache)

    sim_matrices = {
        "Embedding": embed_sim,
        "Mechanism": mechanism_sim,
        "Topic": topic_sim,
    }

    stage_a_measurement_invariance(texts, sim_matrices)
    stage_b_latent_geometry(texts, sim_matrices)


if __name__ == "__main__":
    main()
