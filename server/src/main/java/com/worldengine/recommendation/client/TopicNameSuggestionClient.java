package com.worldengine.recommendation.client;

import java.util.List;
import java.util.stream.Collectors;
import org.springframework.stereotype.Component;

@Component
public class TopicNameSuggestionClient {

    private static final String PROMPT = """
        다음은 한 Topic으로 묶인 스크랩 요약들이다. 이 스크랩들을 관통하는 \
        구체적인 주제를 짧은 한글 명사구로 지어라(예: 부산 해변 여행, Spring \
        Boot 학습). 따옴표 없이 이름만 출력하라. 15자 이내로. 다른 설명은 절대 \
        덧붙이지 마라.

        %s
        """;

    private final OpenAiChatClient chatClient;

    public TopicNameSuggestionClient(OpenAiChatClient chatClient) {
        this.chatClient = chatClient;
    }

    public String suggestName(List<String> summaries) {
        String bulletList = summaries.stream()
            .map(summary -> "- " + summary)
            .collect(Collectors.joining("\n"));
        return stripQuotes(chatClient.complete(PROMPT.formatted(bulletList)));
    }

    /**
     * 프롬프트 예시에 따옴표를 넣었더니 모델이 출력에도 따옴표를 그대로
     * 붙이는 경우가 실제로 나옴(실사용 검증 중 발견) - 프롬프트도
     * 고쳤지만 모델 출력은 100% 통제가 안 되니 방어적으로 한 번 더 벗김.
     */
    private String stripQuotes(String text) {
        String trimmed = text.trim();
        if (trimmed.length() >= 2 && trimmed.startsWith("\"") && trimmed.endsWith("\"")) {
            return trimmed.substring(1, trimmed.length() - 1).trim();
        }
        return trimmed;
    }
}
