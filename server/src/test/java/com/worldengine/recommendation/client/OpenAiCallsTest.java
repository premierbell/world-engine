package com.worldengine.recommendation.client;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.ResourceAccessException;

/**
 * OpenAI 호출 재시도 정책 - 429와 5xx만 재시도하고, 타임아웃(ResourceAccessException)과 4xx는 바로 던진다.
 * 대기 시간은 0으로 줘서 테스트가 느려지지 않게 한다.
 */
class OpenAiCallsTest {

    private static final long NO_BACKOFF = 0;

    @Test
    void 일시적인_5xx는_재시도해서_성공한다() {
        AtomicInteger calls = new AtomicInteger();

        String result = OpenAiCalls.withRetry(() -> {
            if (calls.incrementAndGet() < 3) {
                throw serverError(HttpStatus.SERVICE_UNAVAILABLE);
            }
            return "ok";
        }, NO_BACKOFF);

        assertThat(result).isEqualTo("ok");
        assertThat(calls).hasValue(3);
    }

    @Test
    void 요청한도_초과_429도_재시도한다() {
        AtomicInteger calls = new AtomicInteger();

        String result = OpenAiCalls.withRetry(() -> {
            if (calls.incrementAndGet() == 1) {
                throw clientError(HttpStatus.TOO_MANY_REQUESTS);
            }
            return "ok";
        }, NO_BACKOFF);

        assertThat(result).isEqualTo("ok");
        assertThat(calls).hasValue(2);
    }

    @Test
    void 서버오류_5xx가_계속되면_최대_3번까지만_시도하고_던진다() {
        AtomicInteger calls = new AtomicInteger();

        assertThatThrownBy(() -> OpenAiCalls.withRetry(() -> {
            calls.incrementAndGet();
            throw serverError(HttpStatus.INTERNAL_SERVER_ERROR);
        }, NO_BACKOFF)).isInstanceOf(HttpServerErrorException.class);

        assertThat(calls).hasValue(3);
    }

    @Test
    void 타임아웃은_재시도하지_않는다() {
        AtomicInteger calls = new AtomicInteger();

        assertThatThrownBy(() -> OpenAiCalls.withRetry(() -> {
            calls.incrementAndGet();
            throw new ResourceAccessException("I/O error: request timed out");
        }, NO_BACKOFF)).isInstanceOf(ResourceAccessException.class);

        assertThat(calls).hasValue(1);
    }

    @Test
    void 요청_자체가_잘못된_4xx는_재시도하지_않는다() {
        AtomicInteger calls = new AtomicInteger();

        assertThatThrownBy(() -> OpenAiCalls.withRetry(() -> {
            calls.incrementAndGet();
            throw clientError(HttpStatus.BAD_REQUEST);
        }, NO_BACKOFF)).isInstanceOf(HttpClientErrorException.class);

        assertThat(calls).hasValue(1);
    }

    private static HttpServerErrorException serverError(HttpStatus status) {
        return HttpServerErrorException.create(status, status.getReasonPhrase(), HttpHeaders.EMPTY, null, null);
    }

    private static HttpClientErrorException clientError(HttpStatus status) {
        return HttpClientErrorException.create(status, status.getReasonPhrase(), HttpHeaders.EMPTY, null, null);
    }
}
