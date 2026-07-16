"""World Engine V0 - CLI entrypoint.

Step 2-2: 문자열 입력 -> Embedding -> 차원/미리보기 출력.
아직 Island, Threshold, Similarity, Label, Topic은 없다.
"""

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from embedding_provider import OpenAIEmbeddingProvider

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

    text = "Spring Boot JPA 성능 튜닝"
    vector = provider.embed(text)

    console.print(Panel.fit("🌍 World Engine V0", border_style="cyan"))
    console.print(f"[bold]Embedding Provider[/bold]  ✓ {provider_name}")
    console.print(f"[bold]Model[/bold]               ✓ {model}")
    console.print(f"[bold]Input[/bold]               {text}")
    console.print(f"[bold]Dimension[/bold]           {len(vector)}")
    console.print(f"[bold]Preview[/bold]              {vector[:5]}")


if __name__ == "__main__":
    main()
