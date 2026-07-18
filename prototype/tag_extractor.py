"""AI는 태그(구조화된 이해)만 준다. 태그를 어떻게 비교/판단할지는 알고리즘이 결정한다
(ai_rules.md Rule 1, Rule 2) - Embedding과 마찬가지로 "이해" 계층이지, 판단 계층이
아니다. LabelGenerator(label_generator.py)는 이미 확정된 클러스터에 이름을 붙이는
표현 계층이고, TagExtractor는 그보다 이전 단계 - 클러스터링 자체가 일어나기 전에
스크랩 하나하나에서 구조화된(태그 집합) 정보를 뽑아내는 역할이다.

Research Question #5("Similarity만으로 Topic Identity를 만들 수 있는가?") 실험용으로
신설 - Finding #008(embedding cosine similarity가 Topic Identity를 판별 못 함)이후,
연속적인 유사도가 아니라 이산적인(discrete) 태그 겹침이 더 나은 신호인지 검증한다.
"""

from abc import ABC, abstractmethod

from openai import OpenAI

_PROMPT = (
    "다음 스크랩 요약에서 핵심 기술/개념 키워드를 3~5개 추출하라. 각 키워드는 "
    "영어 소문자 snake_case 1~2단어로 정규화하라(예: transformer, fine_tuning, "
    "vector_db). 쉼표로만 구분해서 키워드만 출력하라 - 설명, 번호, 다른 말은 "
    "덧붙이지 마라.\n\n스크랩: "
)


class TagExtractor(ABC):
    @abstractmethod
    def extract(self, text: str) -> list[str]:
        """단일 스크랩 텍스트에서 구조화된 키워드 태그를 추출한다. 이 태그가 어떻게
        비교되고 attach 판단에 쓰일지는 이 클래스의 책임이 아니다."""
        raise NotImplementedError


class OpenAITagExtractor(TagExtractor):
    def __init__(self, model: str):
        self.model = model
        self.client = OpenAI()

    def extract(self, text: str) -> list[str]:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[{"role": "user", "content": _PROMPT + text}],
        )
        raw = response.choices[0].message.content.strip()
        return [tag.strip().lower() for tag in raw.split(",") if tag.strip()]


_HIERARCHICAL_PROMPT = (
    "다음 스크랩 요약을 읽고, 두 계층으로 나눠 핵심 키워드를 추출하라.\n\n"
    "LEVEL1: 이 내용이 속하는 가장 넓은 상위 기술/개념 범주를 1개만 답하라 - "
    "이 스크랩이 어떤 사람이 저장한 노트 모음의 일부라면, 그 사람이 \"이건 무슨 "
    "주제 폴더에 넣을까\"라고 물었을 때 나올 법한 큰 카테고리 이름이어야 한다.\n"
    "LEVEL2: 이 내용이 구체적으로 다루는 세부 기법/개념을 2~4개 답하라.\n\n"
    "예시(도메인은 다르지만 형식만 참고하라): "
    "\"에어프라이어로 감자튀김 바삭하게 굽는 법, 기름 없이 180도 15분\"이라면\n"
    "LEVEL1: air_frying\n"
    "LEVEL2: potato_fries, oil_free_cooking, temperature_control\n\n"
    "출력은 정확히 다음 형식으로만 답하라(다른 설명은 절대 덧붙이지 마라):\n"
    "LEVEL1: <태그>\n"
    "LEVEL2: <태그1>, <태그2>, ...\n\n"
    "영어 소문자 snake_case만 사용하라.\n\n스크랩: "
)


class HierarchicalTagExtractor:
    """TagExtractor(flat, Experiment #37)의 Recall 부족(Error Analysis, Experiment
    #38)이 정보 부족이 아니라 추상화 수준(level) 불일치 때문이라는 가설을 검증하기
    위한 2계층 버전 - LEVEL1(넓은 상위 범주)/LEVEL2(구체적 하위 개념)를 함께
    추출한다. AI는 여전히 "이해"만 제공(계층 정보 포함)하고, 그 계층을 어떻게
    비교/판단할지는 알고리즘 몫이다(ai_rules.md Rule 1)."""

    def __init__(self, model: str):
        self.model = model
        self.client = OpenAI()

    def extract(self, text: str) -> tuple[list[str], list[str]]:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[{"role": "user", "content": _HIERARCHICAL_PROMPT + text}],
        )
        raw = response.choices[0].message.content.strip()
        level1: list[str] = []
        level2: list[str] = []
        for line in raw.splitlines():
            if line.upper().startswith("LEVEL1:"):
                level1 = [t.strip().lower() for t in line.split(":", 1)[1].split(",") if t.strip()]
            elif line.upper().startswith("LEVEL2:"):
                level2 = [t.strip().lower() for t in line.split(":", 1)[1].split(",") if t.strip()]
        return level1, level2
