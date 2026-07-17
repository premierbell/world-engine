"""AI는 이름표만 준다. 어디에 속하는지(Island/Topic 배치)는 알고리즘이 이미 결정했다
(ai_rules.md Rule 1, Rule 2) - LabelGenerator는 이미 확정된 클러스터에 사람이 읽을 수
있는 이름을 붙이는 표현(presentation) 계층이지, 구조를 바꾸는 판단 계층이 아니다.

Temperature 0은 출력 변동을 줄여주지만 완전한 결정론을 보장하지는 않는다. World Engine에서
결정론이 필요한 것은 구조(클러스터링)이며, Label은 표현 계층이므로 약간의 변동은 허용된다.
"""

from abc import ABC, abstractmethod
from typing import Literal

from openai import OpenAI

Level = Literal["topic", "island"]

_PROMPTS: dict[Level, str] = {
    "topic": (
        "다음은 사용자가 저장한 스크랩 요약들이다. 이 스크랩들을 관통하는 공통 주제를 "
        "2~5단어의 짧은 한국어 명사구로 답하라. 설명이나 문장이 아니라 이름표(label)여야 "
        "한다. 다른 말은 덧붙이지 말고 이름표만 출력하라."
    ),
    "island": (
        "다음은 하나의 상위 관심 영역 안에 있는 세부 주제(Topic)들의 이름이다. 이 "
        "세부 주제들을 전부 포괄하는 상위 관심 분야를 2~5단어의 짧은 한국어 명사구로 "
        "답하라. 설명이나 문장이 아니라 이름표(label)여야 한다. 다른 말은 덧붙이지 "
        "말고 이름표만 출력하라."
    ),
}


class LabelGenerator(ABC):
    @abstractmethod
    def generate(self, texts: list[str], level: Level) -> str:
        """여러 텍스트(스크랩 요약 또는 하위 Topic 라벨)를 관통하는 짧은 라벨을 반환한다.

        어떤 텍스트를 몇 개나 보낼지(대표 샘플링 여부 등)는 호출하는 쪽의 책임이다 -
        이 클래스는 판단하지 않는다.
        """
        raise NotImplementedError


class OpenAILabelGenerator(LabelGenerator):
    def __init__(self, model: str):
        self.model = model
        self.client = OpenAI()

    def generate(self, texts: list[str], level: Level = "topic") -> str:
        prompt = _PROMPTS[level] + "\n\n" + "\n".join(f"- {t}" for t in texts)
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
