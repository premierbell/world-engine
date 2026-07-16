"""Experiment #3: 텍스트 길이(제목/제목+요약/본문)가 같은 Topic 내부 유사도를 얼마나 강하게 모으는지 확인한다.

가설: 텍스트가 길어질수록(title -> summary -> body) 같은 Topic 쌍의 유사도와 다른 Topic 쌍의 유사도 사이 격차(gap)가 커질 것이다.
"""

import json
from itertools import combinations

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from embedding_provider import OpenAIEmbeddingProvider
from similarity import cosine_similarity

console = Console()

LENGTH_TIERS = ["title", "summary", "body"]


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_articles(path: str) -> dict[str, dict]:
    with open(path) as f:
        return json.load(f)


def main() -> None:
    load_dotenv()
    config = load_config()
    provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])

    articles = load_articles("../golden_dataset/length_comparison.json")
    keys = list(articles.keys())

    table = Table(title="텍스트 길이별 Topic 내부/간 유사도")
    for col in ("Length", "Same-topic Avg", "Cross-topic Avg", "Gap"):
        table.add_column(col)

    for tier in LENGTH_TIERS:
        vectors = {key: provider.embed(articles[key][tier]) for key in keys}

        same_sims, cross_sims = [], []
        for a, b in combinations(keys, 2):
            sim = cosine_similarity(vectors[a], vectors[b])
            if articles[a]["topic"] == articles[b]["topic"]:
                same_sims.append(sim)
            else:
                cross_sims.append(sim)

        same_avg = sum(same_sims) / len(same_sims)
        cross_avg = sum(cross_sims) / len(cross_sims)
        table.add_row(tier, f"{same_avg:.4f}", f"{cross_avg:.4f}", f"{same_avg - cross_avg:.4f}")

    console.print(table)


if __name__ == "__main__":
    main()