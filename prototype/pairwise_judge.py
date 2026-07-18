"""AI는 두 스크랩 사이의 관계(같은 구체적 주제를 다루는가)에 대한 판단 점수만
준다 - 최종 결정(Anchor 배정 등)은 여전히 알고리즘 몫이다(ai_rules.md Rule 1).
지금까지(embedding, tag)는 "이해"의 단위가 문서 하나였고 그게 Finding
#008/#009가 드러낸 한계의 근원이었다 - 여기서는 "이해"의 단위를 문서 쌍
(relation)으로 바꾼다. Research Question #8("Topic Identity는 pairwise
semantic judgment로 복원 가능한가?") 검증용으로 신설.
"""

from abc import ABC, abstractmethod

from openai import OpenAI

_PROMPT = (
    "다음 두 스크랩 요약을 비교해서, 둘이 같은 구체적인 하위 주제/기술을 다루고 "
    "있는지 0.0~1.0 사이의 점수로 평가하라. 같은 상위 분야(예: 둘 다 AI 관련, "
    "둘 다 백엔드 관련)라는 이유만으로 높은 점수를 주면 안 된다 - 실제로 같은 "
    "구체적 개념/기법을 다루고 있는지만 봐야 한다. 점수 숫자 하나만 출력하라 "
    "(예: 0.85). 다른 설명은 절대 덧붙이지 마라.\n\n"
    "스크랩 A: {a}\n스크랩 B: {b}"
)


class PairwiseJudge(ABC):
    @abstractmethod
    def score(self, text_a: str, text_b: str) -> float:
        """두 스크랩이 같은 구체적 하위 주제를 다루는 정도를 0~1로 반환한다.
        이 점수로 무엇을 할지(threshold, Anchor 배정 등)는 이 클래스의 책임이
        아니다."""
        raise NotImplementedError


class OpenAIPairwiseJudge(PairwiseJudge):
    def __init__(self, model: str):
        self.model = model
        self.client = OpenAI()

    def score(self, text_a: str, text_b: str) -> float:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[{"role": "user", "content": _PROMPT.format(a=text_a, b=text_b)}],
        )
        raw = response.choices[0].message.content.strip()
        try:
            return max(0.0, min(1.0, float(raw)))
        except ValueError:
            return 0.5  # 파싱 실패 - 무정보 값으로 처리(호출부에서 실패 건수 별도 집계 권장)
