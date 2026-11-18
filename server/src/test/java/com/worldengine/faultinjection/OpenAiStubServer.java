package com.worldengine.faultinjection;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.EnumMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * [측정 도구] OpenAI API 대신 응답하는 로컬 가짜 서버. 단계별로 정상/오류/무응답을 골라 낼 수 있다.
 * JDK 내장 HttpServer만 써서 의존성을 추가하지 않는다.
 *
 * 요청을 단계로 나누는 기준:
 * - /embeddings → EMBEDDING
 * - /chat/completions 중 프롬프트에 "0.0~1.0"이 있으면 → JUDGE (LlmPairwiseJudgeClient의 두 프롬프트)
 * - 나머지 /chat/completions → SUMMARY (ContentSummaryClient)
 */
final class OpenAiStubServer {

    enum Stage { SUMMARY, EMBEDDING, JUDGE }

    enum Behavior {
        OK,
        ERROR_500,
        /** 매번 429 - OpenAiChatClient의 429 재시도가 몇 번, 얼마나 기다리는지 본다 */
        ERROR_429,
        /** 첫 호출만 503, 그 뒤로는 정상 - 일시 장애에서 자동으로 회복하는지 본다 */
        ERROR_503_ONCE,
        /** 응답하지 않고 releaseHung()이 불릴 때까지 붙잡는다 */
        HANG
    }

    private static final float[] EMBEDDING = {1.0f, 0.0f, 0.0f};
    private static final long HANG_SAFETY_LIMIT_SECONDS = 300;

    private final HttpServer server;
    private final Map<Stage, Behavior> behaviors = new ConcurrentHashMap<>();
    private final Map<Stage, AtomicInteger> calls = new EnumMap<>(Stage.class);
    private volatile CountDownLatch hangRelease = new CountDownLatch(1);

    private OpenAiStubServer(HttpServer server) {
        this.server = server;
        for (Stage stage : Stage.values()) {
            calls.put(stage, new AtomicInteger());
        }
    }

    static OpenAiStubServer start() {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            OpenAiStubServer stub = new OpenAiStubServer(server);
            server.createContext("/", stub::handle);
            // 기본 executor는 요청을 한 스레드에서 순서대로 처리한다 - 병렬 LLM 호출과 무응답을 재현하려면 요청마다 스레드 필요
            server.setExecutor(Executors.newThreadPerTaskExecutor(Thread.ofVirtual().factory()));
            server.start();
            return stub;
        } catch (IOException e) {
            throw new IllegalStateException("가짜 OpenAI 서버 시작 실패", e);
        }
    }

    String baseUrl() {
        return "http://127.0.0.1:" + server.getAddress().getPort() + "/v1";
    }

    void reset(Map<Stage, Behavior> setup) {
        releaseHung();
        hangRelease = new CountDownLatch(1);
        behaviors.clear();
        behaviors.putAll(setup);
        calls.values().forEach(counter -> counter.set(0));
    }

    void releaseHung() {
        hangRelease.countDown();
    }

    String callSummary() {
        return "요약 %d / 임베딩 %d / 판정 %d".formatted(
            calls.get(Stage.SUMMARY).get(), calls.get(Stage.EMBEDDING).get(), calls.get(Stage.JUDGE).get());
    }

    void stop() {
        releaseHung();
        server.stop(0);
    }

    private void handle(HttpExchange exchange) throws IOException {
        String path = exchange.getRequestURI().getPath();
        String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
        Stage stage = path.endsWith("/embeddings") ? Stage.EMBEDDING
            : body.contains("0.0~1.0") ? Stage.JUDGE
            : Stage.SUMMARY;
        int callNumber = calls.get(stage).incrementAndGet();

        switch (behaviors.getOrDefault(stage, Behavior.OK)) {
            case OK -> respondOk(exchange, stage);
            case ERROR_500 -> respond(exchange, 500, errorJson("stub 500"));
            case ERROR_429 -> respond(exchange, 429, errorJson("stub rate limit"));
            case ERROR_503_ONCE -> {
                if (callNumber == 1) {
                    respond(exchange, 503, errorJson("stub 503"));
                } else {
                    respondOk(exchange, stage);
                }
            }
            case HANG -> {
                awaitRelease();
                respondOk(exchange, stage);
            }
        }
    }

    private void awaitRelease() {
        try {
            hangRelease.await(HANG_SAFETY_LIMIT_SECONDS, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    private void respondOk(HttpExchange exchange, Stage stage) throws IOException {
        String json = switch (stage) {
            case SUMMARY -> chatJson("가짜 서버가 돌려준 테스트 요약입니다.");
            case JUDGE -> chatJson("0.8");
            case EMBEDDING -> "{\"data\":[{\"embedding\":[%s,%s,%s]}]}".formatted(EMBEDDING[0], EMBEDDING[1], EMBEDDING[2]);
        };
        respond(exchange, 200, json);
    }

    private static String chatJson(String content) {
        return "{\"choices\":[{\"message\":{\"role\":\"assistant\",\"content\":\"" + content + "\"}}]}";
    }

    private static String errorJson(String message) {
        return "{\"error\":{\"message\":\"" + message + "\"}}";
    }

    private static void respond(HttpExchange exchange, int status, String json) throws IOException {
        byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json");
        try {
            exchange.sendResponseHeaders(status, bytes.length);
            try (OutputStream out = exchange.getResponseBody()) {
                out.write(bytes);
            }
        } catch (IOException e) {
            // 클라이언트가 타임아웃으로 먼저 끊은 경우 - 측정에는 영향 없음
        } finally {
            exchange.close();
        }
    }
}
