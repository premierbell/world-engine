package com.worldengine.recommendation.client;

import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

@Tag("live")
class LlmPairwiseJudgeClientLiveTest {

    private final LlmPairwiseJudgeClient client = new LlmPairwiseJudgeClient(
        System.getenv("OPENAI_API_KEY"),
        "gpt-4o-mini"
    );

    @Test
    void scoresRelatedTextsHigherThanUnrelatedTexts() {
        double related = client.score(
            "Docker는 컨테이너 기반 가상화 플랫폼이다.",
            "Kubernetes는 컨테이너 오케스트레이션 도구다."
        );
        double unrelated = client.score(
            "Docker는 컨테이너 기반 가상화 플랫폼이다.",
            "오늘 점심은 김치찌개를 먹었다."
        );

        assertTrue(related > unrelated);
    }
}
