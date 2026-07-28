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

    @Test
    void mechanismScoresSameConcreteTopicHigherThanDifferentTopic() {
        double sameTopic = client.scoreMechanism(
            "제주도 한라산 등산 코스 총정리, 성판악 코스와 관음사 코스 비교",
            "한라산 등반 준비물과 최적 등산 시기 안내"
        );
        double differentTopic = client.scoreMechanism(
            "제주도 한라산 등산 코스 총정리, 성판악 코스와 관음사 코스 비교",
            "부산 해운대 해수욕장 근처 맛집과 야경 명소 추천"
        );

        assertTrue(sameTopic > differentTopic);
    }
}
