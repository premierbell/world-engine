"""AI는 두 스크랩 사이의 관계(같은 구체적 주제를 다루는가)에 대한 판단 점수만
준다 - 최종 결정(Anchor 배정 등)은 여전히 알고리즘 몫이다(ai_rules.md Rule 1).
지금까지(embedding, tag)는 "이해"의 단위가 문서 하나였고 그게 Finding
#008/#009가 드러낸 한계의 근원이었다 - 여기서는 "이해"의 단위를 문서 쌍
(relation)으로 바꾼다. Research Question #8("Topic Identity는 pairwise
semantic judgment로 복원 가능한가?") 검증용으로 신설.
"""

from abc import ABC, abstractmethod

from openai import OpenAI

_PROMPTS = {
    # Experiment #45~49에서 쓴 원래 프롬프트 - "구체적 기법이 같은가"를 명시적으로
    # 요구한다. Finding #012/#013(Mechanism 수준 신호)는 이 프롬프트의 결과다.
    "mechanism": (
        "다음 두 스크랩 요약을 비교해서, 둘이 같은 구체적인 하위 주제/기술을 다루고 "
        "있는지 0.0~1.0 사이의 점수로 평가하라. 같은 상위 분야(예: 둘 다 AI 관련, "
        "둘 다 백엔드 관련)라는 이유만으로 높은 점수를 주면 안 된다 - 실제로 같은 "
        "구체적 개념/기법을 다루고 있는지만 봐야 한다. 점수 숫자 하나만 출력하라 "
        "(예: 0.85). 다른 설명은 절대 덧붙이지 마라.\n\n"
        "스크랩 A: {a}\n스크랩 B: {b}"
    ),
    # Experiment #50 신설 - mechanism 프롬프트와 정반대 지시. Finding #013의
    # 원인이 "LLM의 semantic prior"인지 "Prompt Objective"인지 분리하기 위한
    # 통제 실험용 프롬프트다.
    "topic": (
        "다음 두 스크랩 요약을 비교해서, 둘이 같은 넓은 주제/관심 분야를 다루고 "
        "있는지 0.0~1.0 사이의 점수로 평가하라. 구체적인 세부 기법이나 개념이 "
        "다르더라도, 같은 상위 주제 영역(예: 둘 다 Fine-tuning 관련, 둘 다 "
        "Transformer 아키텍처 관련)이면 높은 점수를 줘야 한다 - 완전히 다른 상위 "
        "주제 영역을 다룰 때만 낮은 점수를 줘라. 점수 숫자 하나만 출력하라 "
        "(예: 0.85). 다른 설명은 절대 덧붙이지 마라.\n\n"
        "스크랩 A: {a}\n스크랩 B: {b}"
    ),
    # Experiment #53 신설 - Mechanism 프롬프트의 Tree-like 행동(Experiment #52)이
    # prompt wording의 인공물(M1)인지 LLM 내재 구조(M2)인지 분리하기 위한 대조
    # 프롬프트. "같은 개념/기법인가"라는 위계적 판단 자체를 요구하지 않는다.
    "neutral": (
        "다음 두 스크랩 요약이 얼마나 밀접하게 관련되어 있는지 0.0~1.0 사이의 "
        "점수로 평가하라. '같은 주제인가/다른 주제인가'를 판단하지 말고, 단순히 "
        "두 내용이 서로 얼마나 가깝게 연관되어 있다고 느껴지는지만 평가하라. "
        "점수 숫자 하나만 출력하라(예: 0.85). 다른 설명은 절대 덧붙이지 마라.\n\n"
        "스크랩 A: {a}\n스크랩 B: {b}"
    ),
    "relation": (
        "다음 두 스크랩 요약을 비교해서, 연구자 입장에서 두 내용을 함께 공부할 "
        "가치가 얼마나 있는지 0.0~1.0 사이의 점수로 평가하라. 이 두 문서는 동일한 "
        "주제/기법을 다루지 않아도 좋다 - 같은 개념인지 아닌지를 판단하지 말고, "
        "함께 놓고 보면 서로 도움이 되는 정도만 평가하라. 점수 숫자 하나만 "
        "출력하라(예: 0.85). 다른 설명은 절대 덧붙이지 마라.\n\n"
        "스크랩 A: {a}\n스크랩 B: {b}"
    ),
}


class PairwiseJudge(ABC):
    @abstractmethod
    def score(self, text_a: str, text_b: str, mode: str = "mechanism") -> float:
        """두 스크랩이 같은 주제를 다루는 정도를 0~1로 반환한다. mode로 판단
        해상도(mechanism=구체적 기법 수준, topic=넓은 주제 수준)를 명시적으로
        고른다 - 이 점수로 무엇을 할지(threshold, Anchor 배정 등)는 이 클래스의
        책임이 아니다."""
        raise NotImplementedError


class OpenAIPairwiseJudge(PairwiseJudge):
    def __init__(self, model: str):
        self.model = model
        self.client = OpenAI()

    def score(self, text_a: str, text_b: str, mode: str = "mechanism") -> float:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[{"role": "user", "content": _PROMPTS[mode].format(a=text_a, b=text_b)}],
        )
        raw = response.choices[0].message.content.strip()
        try:
            return max(0.0, min(1.0, float(raw)))
        except ValueError:
            return 0.5  # 파싱 실패 - 무정보 값으로 처리(호출부에서 실패 건수 별도 집계 권장)
