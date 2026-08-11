package com.worldengine.recommendation.client;

import org.springframework.stereotype.Component;

@Component
public class LlmPairwiseJudgeClient {

    private static final String NEUTRAL_PROMPT = """
        다음 두 스크랩 요약이 얼마나 밀접하게 관련되어 있는지 0.0~1.0 사이의 점수로 평가하라. \
        '같은 주제인가/다른 주제인가'를 판단하지 말고, 단순히 두 내용이 서로 얼마나 가깝게 \
        연관되어 있다고 느껴지는지만 평가하라. 점수 숫자 하나만 출력하라(예: 0.85). \
        다른 설명은 절대 덧붙이지 마라.

        스크랩 A: %s
        스크랩 B: %s
        """;

    /**
     * V0 prototype/pairwise_judge.py의 "mechanism" objective를 그대로 포팅 -
     * Finding #012(AUC 0.82~0.94)의 근거였던 프롬프트. Neutral과 반대로 "같은
     * 구체적 대상/개념인가"를 명시적으로 요구한다 - Island 배정(넓은 판단,
     * Neutral)과 달리 Topic 후보 생성(세밀한 판단)에 쓴다(docs/v2_design.md).
     */
    private static final String MECHANISM_PROMPT = """
        다음 두 스크랩 요약을 비교해서, 둘이 같은 구체적인 하위 주제/대상을 다루고 있는지 \
        0.0~1.0 사이의 점수로 평가하라. 같은 상위 분야라는 이유만으로 높은 점수를 주면 안 \
        된다 - 실제로 같은 구체적 개념/대상을 다루고 있는지만 봐야 한다. 점수 숫자 하나만 \
        출력하라(예: 0.85). 다른 설명은 절대 덧붙이지 마라.

        스크랩 A: %s
        스크랩 B: %s
        """;

    private final OpenAiChatClient chatClient;

    public LlmPairwiseJudgeClient(OpenAiChatClient chatClient) {
        this.chatClient = chatClient;
    }

    public double score(String textA, String textB) {
        return parseScore(chatClient.complete(NEUTRAL_PROMPT.formatted(textA, textB)));
    }

    public double scoreMechanism(String textA, String textB) {
        return parseScore(chatClient.complete(MECHANISM_PROMPT.formatted(textA, textB)));
    }

    private double parseScore(String raw) {
        try {
            double parsed = Double.parseDouble(raw);
            return Math.max(0.0, Math.min(1.0, parsed));
        } catch (NumberFormatException e) {
            return 0.5;
        }
    }
}
