"""Experiment #2: 카테고리별 텍스트의 pairwise cosine similarity 분포 관찰.

목적: 같은 카테고리 내 유사도와 카테고리 간 유사도가 실제로 구분되는지 확인해
threshold 후보를 찾는다. 아직 threshold를 코드에 적용하지는 않는다.
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


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_categories(path: str) -> dict[str, list[str]]:
    with open(path) as f:
        return json.load(f)


def main() -> None:
    load_dotenv()
    config = load_config()
    provider = OpenAIEmbeddingProvider(model=config["embedding"]["model"])

    categories = load_categories("../golden_dataset/categories.json")

    vectors: dict[str, list[float]] = {}
    text_category: dict[str, str] = {}
    for category, texts in categories.items():
        for text in texts:
            vectors[text] = provider.embed(text)
            text_category[text] = category

    all_texts = list(vectors.keys())

    within: dict[str, list[float]] = {c: [] for c in categories}
    across: dict[tuple[str, str], list[float]] = {}

    for a, b in combinations(all_texts, 2):
        sim = cosine_similarity(vectors[a], vectors[b])
        cat_a, cat_b = text_category[a], text_category[b]
        if cat_a == cat_b:
            within[cat_a].append(sim)
        else:
            pair = tuple(sorted((cat_a, cat_b)))
            across.setdefault(pair, []).append(sim)

    within_table = Table(title="같은 카테고리 내 유사도")
    for col in ("Category", "Avg", "Min", "Max", "N"):
            within_table.add_column(col)
    for category, sims in within.items():
        within_table.add_row(category, f"{sum(sims)/len(sims):.4f}",
            f"{min(sims):.4f}", f"{max(sims):.4f}", str(len(sims)))
    console.print(within_table)

    across_table = Table(title="카테고리 간 유사도")
    for col in ("Pair", "Avg", "Min", "Max", "N"):
        across_table.add_column(col)
    for pair, sims in across.items():
        across_table.add_row(" ↔ ".join(pair), f"{sum(sims)/len(sims):.4f}",
            f"{min(sims):.4f}", f"{max(sims):.4f}", str(len(sims)))
    console.print(across_table)


if __name__ == "__main__":
    main()




