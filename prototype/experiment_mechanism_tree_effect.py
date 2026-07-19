"""Experiment #53: Mechanism Tree Effect - Prompt Artifact(M1) or Model Prior(M2)?

Experiment #52는 Mechanism 프롬프트가 극단적으로 Tree처럼 행동한다는 걸
발견했다(ultrametric violation 0.8%, cophenetic corr 0.921). 이 실험은
그 원인을 분리한다:

- M1 (Prompt Artifact): "같은 구체적 개념/기법인가"라는 위계적 판단을
  강제하는 prompt wording 자체가 Tree 구조를 만들어낸다. Prompt에서 그
  요구를 빼면 Tree-likeness가 무너진다.
- M2 (Model Prior): LLM이 갖고 있는 semantic knowledge 자체가 원래
  hierarchical하다. Prompt를 바꿔도 Tree-likeness가 유지된다.

같은 36개 curated sample, 같은 630개 pair에 대해 새 프롬프트 두 개만
바꿔서(mechanism 판단을 요구하지 않는 neutral/relation, `pairwise_judge.py`)
점수를 다시 매기고, Experiment #52와 동일한 Stage B 지표
(ultrametric violation, cophenetic, MDS stress)로 비교한다.

예측: M1이 맞다면 Neutral/Relation의 Tree 적합도가 Mechanism보다
뚜렷이 낮아야 한다. M2가 맞다면 셋 다 비슷하게 Tree-like해야 한다.
"""

import itertools
import json

import yaml
from dotenv import load_dotenv
from rich.console import Console

from experiment_anchor_model import load_virtual_user
from experiment_pairwise_granularity import MECHANISM_LABELS, curated_sample
from experiment_resolution_ontology import (
    build_score_matrix,
    pair_key,
    stage_b_latent_geometry,
)
from pairwise_judge import OpenAIPairwiseJudge

console = Console()

MECHANISM_CACHE_PATH = "pairwise_judgment_cache.json"
NEUTRAL_CACHE_PATH = "pairwise_judgment_neutral_cache.json"
RELATION_CACHE_PATH = "pairwise_judgment_relation_cache.json"


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_cache(path: str) -> dict[str, float]:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_cache(path: str, cache: dict[str, float]) -> None:
    with open(path, "w") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def score_all_pairs(
    texts: list[str], judge: OpenAIPairwiseJudge, mode: str, cache: dict[str, float], cache_path: str
) -> None:
    pairs = list(itertools.combinations(texts, 2))
    done = 0
    for a, b in pairs:
        key = pair_key(a, b)
        if key not in cache:
            cache[key] = judge.score(a, b, mode=mode)
        done += 1
        if done % 100 == 0:
            save_cache(cache_path, cache)
            console.print(f"  [{mode}] {done}/{len(pairs)}")
    save_cache(cache_path, cache)


def main() -> None:
    load_dotenv()
    config = load_config()
    judge = OpenAIPairwiseJudge(model=config["label"]["model"])

    user = load_virtual_user("../experiments/virtual_users/ai_researcher.json")
    all_scraps = [s for s in user["scraps"] if s["text"] in MECHANISM_LABELS]
    scraps = curated_sample(all_scraps, per_topic_cap=4)
    texts = [s["text"] for s in scraps]
    console.print(f"[bold]표본 {len(texts)}개 (Experiment #47/#50/#52와 동일)[/bold]\n")

    mechanism_cache = load_cache(MECHANISM_CACHE_PATH)
    neutral_cache = load_cache(NEUTRAL_CACHE_PATH)
    relation_cache = load_cache(RELATION_CACHE_PATH)

    console.print("[bold]Neutral 프롬프트로 채점 중...[/bold]")
    score_all_pairs(texts, judge, "neutral", neutral_cache, NEUTRAL_CACHE_PATH)
    console.print("[bold]Relation 프롬프트로 채점 중...[/bold]")
    score_all_pairs(texts, judge, "relation", relation_cache, RELATION_CACHE_PATH)

    sim_matrices = {
        "Mechanism": build_score_matrix(texts, mechanism_cache),
        "Neutral": build_score_matrix(texts, neutral_cache),
        "Relation": build_score_matrix(texts, relation_cache),
    }

    stage_b_latent_geometry(texts, sim_matrices)


if __name__ == "__main__":
    main()
