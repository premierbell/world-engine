"""World Engine V0 - CLI entrypoint.

Step 3: 여러 텍스트를 임베딩하고 쌍별 Cosine Similarity를 출력한다.
아직 Threshold, Island, Label, Topic은 없다.
"""

from itertools import combinations

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from embedding_provider import OpenAIEmbeddingProvider
from similarity import cosine_similarity

console = Console()


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def main() -> None:
    load_dotenv()
    config = load_config()

    provider_name = config["embedding"]["provider"]
    model = config["embedding"]["model"]
    if provider_name != "openai":
        raise NotImplementedError(f"unsupported provider: {provider_name}")
    provider = OpenAIEmbeddingProvider(model=model)

    texts = {
            "A": "Spring Boot 성능 튜닝",
            "B": "Redis 캐싱",
            "C": "손흥민 골",
        }
    vectors = {key: provider.embed(text) for key, text in texts.items()}

    console.print(Panel.fit("🌍 World Engine V0 - Similarity", border_style="cyan"))
    for key_a, key_b in combinations(texts, 2):
        sim = cosine_similarity(vectors[key_a], vectors[key_b])
        console.print(f"{texts[key_a]!r:30} vs {texts[key_b]!r:20} -> [bold]{sim:.4f}[/bold]")


if __name__ == "__main__":
    main()
