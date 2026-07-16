"""AI는 벡터만 준다. 판단은 알고리즘이 한다 (ai_rules.md Rule 1, Rule 2).

이 모듈은 그 경계를 코드로 강제한다 - EmbeddingProvider는 embed() 하나만 노출하고,
Nearest Neighbor / Threshold / Growth 같은 판단은 절대 여기 들어오지 않는다.
"""

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """단일 텍스트에 대한 임베딩 벡터를 반환한다."""
        raise NotImplementedError


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model: str):
        self.model = model
        # TODO(Step 2): OpenAI 클라이언트 연결 및 embed() 구현
        raise NotImplementedError
