package com.worldengine.recommendation.client;

import java.time.Duration;
import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

/**
 * OpenAI Embeddings API 호출 - 공식 Java SDK가 없어서 Spring의
 * RestClient로 직접 호출한다(jsoup/PDFBox를 직접 쓴 것과 같은 이유).
 * docs/v1_design.md Scrap Flow 4단계(Cosine 후보 추리기)의 입력을 만든다.
 */
@Component
public class OpenAiEmbeddingClient {

    private static final Duration READ_TIMEOUT = Duration.ofSeconds(10);

    private final RestClient restClient;
    private final String model;

    public OpenAiEmbeddingClient(
        @Value("${openai.api-key}") String apiKey,
        @Value("${openai.base-url}") String baseUrl,
        @Value("${openai.embedding-model}") String model) {
        this.restClient = RestClient.builder()
            .requestFactory(OpenAiCalls.requestFactory(READ_TIMEOUT))
            .baseUrl(baseUrl)
            .defaultHeader("Authorization", "Bearer " + apiKey)
            .build();
        this.model = model;
    }

    public float[] embed(String text) {
        return OpenAiCalls.withRetry(() -> request(text));
    }

    private float[] request(String text) {
        EmbeddingResponse response = restClient.post()
            .uri("/embeddings")
            .body(new EmbeddingRequest(model, text))
            .retrieve()
            .body(EmbeddingResponse.class);

        if (response == null || response.data().isEmpty()) {
            throw new IllegalStateException("OpenAI embeddings 응답이 비어있음");
        }
        return response.data().get(0).embedding();
    }

    private record EmbeddingRequest(String model, String input) {}

    private record EmbeddingResponse(List<EmbeddingData> data) {}

    private record EmbeddingData(float[] embedding) {}

}
