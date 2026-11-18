package com.worldengine.recommendation.client;

import java.net.http.HttpClient;
import java.time.Duration;
import java.util.function.Supplier;
import org.springframework.http.client.ClientHttpRequestFactory;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.HttpServerErrorException;

/**
 * OpenAI 호출 공통 정책 - 타임아웃과 재시도 (experiments/v0_validation.md, 2026-11-18 장애 측정).
 *
 * - 타임아웃: 설정이 없어서 OpenAI가 응답하지 않으면 40초가 지나도 요청이 끝나지 않았다.
 * - 재시도: 429와 5xx(일시 장애)만. 타임아웃은 재시도하지 않는다 - 다시 기다리면 대기 시간이 배로 늘어난다.
 *   4xx(요청 자체가 잘못됨)는 다시 보내도 같은 결과라 재시도하지 않는다.
 */
final class OpenAiCalls {

    private static final Duration CONNECT_TIMEOUT = Duration.ofSeconds(5);
    private static final int MAX_ATTEMPTS = 3;
    private static final long RETRY_BACKOFF_MS = 2000;

    private OpenAiCalls() {}

    static ClientHttpRequestFactory requestFactory(Duration readTimeout) {
        HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(CONNECT_TIMEOUT)
            .build();
        JdkClientHttpRequestFactory factory = new JdkClientHttpRequestFactory(httpClient);
        factory.setReadTimeout(readTimeout);
        return factory;
    }

    static <T> T withRetry(Supplier<T> call) {
        return withRetry(call, RETRY_BACKOFF_MS);
    }

    static <T> T withRetry(Supplier<T> call, long backoffMs) {
        for (int attempt = 1; ; attempt++) {
            try {
                return call.get();
            } catch (HttpClientErrorException.TooManyRequests | HttpServerErrorException e) {
                if (attempt == MAX_ATTEMPTS) {
                    throw e;
                }
                sleep(backoffMs * attempt);
            }
        }
    }

    private static void sleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("재시도 대기 중 인터럽트됨", e);
        }
    }
}
