"""Experiment #4: Title/Summary/Body의 품질(Gap) 대비 비용(토큰)·지연시간을 비교한다.

목적: Experiment #3에서 Body로 갈수록 품질 개선폭이 줄어드는 것으로 보여,
Summary가 실제로 비용 대비 가장 효율적인 지점인지 정량적으로 확인한다.
"""

import json
import time
from itertools import combinations

import tiktoken
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
    model = config["embedding"]["model"]
    provider = OpenAIEmbeddingProvider(model=model)
    encoding = tiktoken.encoding_for_model(model)

    articles = load_articles("../golden_dataset/length_comparison.json")
    keys = list(articles.keys())

    table = Table(title="Title / Summary / Body - 품질 vs 비용 vs 지연시간")
    for col in ("Input", "Gap", "Avg Tokens", "Gap / 1K Tokens", "Latency(s)"):
        table.add_column(col)

    for tier in LENGTH_TIERS:
        token_counts = [len(encoding.encode(articles[key][tier])) for key in keys]
        avg_tokens = sum(token_counts) / len(token_counts)

        start = time.perf_counter()
        vectors = {key: provider.embed(articles[key][tier]) for key in keys}
        elapsed = time.perf_counter() - start

        same_sims, cross_sims = [], []
        for a, b in combinations(keys, 2):
            sim = cosine_similarity(vectors[a], vectors[b])
            if articles[a]["topic"] == articles[b]["topic"]:
                same_sims.append(sim)
            else:
                cross_sims.append(sim)
        gap = sum(same_sims) / len(same_sims) - sum(cross_sims) / len(cross_sims)
        efficiency = gap / avg_tokens * 1000

        table.add_row(tier, f"{gap:.4f}", f"{avg_tokens:.1f}", f"{efficiency:.3f}", f"{elapsed:.2f}")

    console.print(table)


if __name__ == "__main__":
    main()
