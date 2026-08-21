package com.worldengine.recommendation.client;

import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClient;

/**
 * OpenAI Chat Completions 호출 공통 부분(RestClient 설정, 429 재시도) -
 * LlmPairwiseJudgeClient(점수 채점)와 TopicNameSuggestionClient(이름
 * 제안) 둘 다 같은 채팅 API를 다른 프롬프트/파싱으로 쓰는 두 번째
 * 소비자가 생긴 시점에 공통부분만 추출(EmbeddingConverter를 common으로
 * 옮겼을 때와 같은 원칙 - island/service/CoordinateMigrationService
 * 근처 참고).
 */
@Component
public class OpenAiChatClient {

    private static final int MAX_ATTEMPTS = 3;
    private static final long RETRY_BACKOFF_MS = 2000;

    private final RestClient restClient;
    private final String model;

    public OpenAiChatClient(
        @Value("${openai.api-key}") String apiKey,
        @Value("${openai.chat-model}") String model) {
        this.restClient = RestClient.builder()
            .baseUrl("https://api.openai.com/v1")
            .defaultHeader("Authorization", "Bearer " + apiKey)
            .build();
        this.model = model;
    }

    public String complete(String prompt) {
        for (int attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
            try {
                return request(prompt);
            } catch (HttpClientErrorException.TooManyRequests e) {
                if (attempt == MAX_ATTEMPTS) {
                    throw e;
                }
                sleep(RETRY_BACKOFF_MS * attempt);
            }
        }
        throw new IllegalStateException("재시도 로직 도달 불가 지점");
    }

    private String request(String prompt) {
        ChatResponse response = restClient.post()
            .uri("/chat/completions")
            .body(new ChatRequest(model, 0, List.of(new ChatMessage("user", prompt))))
            .retrieve()
            .body(ChatResponse.class);

        if (response == null || response.choices().isEmpty()) {
            throw new IllegalStateException("OpenAI chat completions 응답이 비어있음");
        }

        return response.choices().get(0).message().content().trim();
    }

    private void sleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("재시도 대기 중 인터럽트됨", e);
        }
    }

    private record ChatRequest(String model, int temperature, List<ChatMessage> messages) {}
    private record ChatMessage(String role, String content) {}
    private record ChatResponse(List<Choice> choices) {}
    private record Choice(ChatMessage message) {}
}
