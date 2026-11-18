package com.worldengine.faultinjection;

import static com.worldengine.faultinjection.OpenAiStubServer.Behavior.ERROR_429;
import static com.worldengine.faultinjection.OpenAiStubServer.Behavior.ERROR_500;
import static com.worldengine.faultinjection.OpenAiStubServer.Behavior.ERROR_503_ONCE;
import static com.worldengine.faultinjection.OpenAiStubServer.Behavior.HANG;
import static com.worldengine.faultinjection.OpenAiStubServer.Stage.EMBEDDING;
import static com.worldengine.faultinjection.OpenAiStubServer.Stage.JUDGE;
import static com.worldengine.faultinjection.OpenAiStubServer.Stage.SUMMARY;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

import com.worldengine.extraction.model.ExtractionResult;
import com.worldengine.extraction.model.SourceType;
import com.worldengine.extraction.service.ContentExtractionService;
import com.worldengine.faultinjection.OpenAiStubServer.Behavior;
import com.worldengine.faultinjection.OpenAiStubServer.Stage;
import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.scrap.dto.ScrapCreateResponse;
import com.worldengine.scrap.repository.ScrapRepository;
import com.worldengine.scrap.service.ScrapService;
import com.zaxxer.hikari.HikariDataSource;
import java.sql.Connection;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import javax.sql.DataSource;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

/**
 * [측정 도구] OpenAI가 실패하거나 응답하지 않을 때 스크랩 생성이 어떻게 되는지 잰다 (2026-11-18).
 *
 * - OpenAI 대신 로컬 가짜 서버(OpenAiStubServer)에 붙는다. 실제 OpenAI에는 요청하지 않는다.
 * - 본문 추출(ContentExtractionService)은 Mock - 네트워크 없이 바로 성공한 본문을 돌려준다.
 *   실제로는 이 추출에 최대 10~15초(Playwright)가 걸리고, 그 결과가 함께 버려지는지 본다.
 * - DB는 테스트 기본 H2 인메모리. 시작할 때 H2에 붙었는지 확인하고 아니면 즉시 실패한다.
 * - 무응답 시나리오는 HANG_CAP_SECONDS까지만 기다리고 그 뒤 가짜 서버를 풀어 준다(테스트가 영원히 멈추지 않도록).
 *
 * 사전 고정한 기준 (측정 전에 정함):
 * ① 어떤 OpenAI 장애에서도 추출한 본문은 DB에 남는다 (스크랩 저장됨 = Y)
 * ② OpenAI가 응답하지 않아도 스크랩 생성 요청은 30초 안에 끝난다
 * ③ 1회성 일시 장애(503 한 번)는 사용자 개입 없이 회복된다
 *
 * 실행: ./gradlew benchmarkTest --tests '*OpenAiFailureMeasureTest'
 */
@Tag("benchmark")
@SpringBootTest
class OpenAiFailureMeasureTest {

    private static final long HANG_CAP_SECONDS = 40;
    private static final String URL = "https://example.com/fault-injection";
    private static final String CONTENT = "가짜 본문입니다. ".repeat(30);

    private static final OpenAiStubServer stub = OpenAiStubServer.start();

    @DynamicPropertySource
    static void pointOpenAiToStub(DynamicPropertyRegistry registry) {
        registry.add("openai.base-url", stub::baseUrl);
    }

    @MockitoBean ContentExtractionService contentExtractionService;

    @Autowired ScrapService scrapService;
    @Autowired ScrapRepository scrapRepository;
    @Autowired IslandRepository islandRepository;
    @Autowired DataSource dataSource;

    @AfterAll
    static void stopStub() {
        stub.stop();
    }

    @Test
    void measureScrapCreationUnderOpenAiFailures() throws Exception {
        assertConnectedToInMemoryH2();
        when(contentExtractionService.extract(anyString()))
            .thenReturn(ExtractionResult.success("가짜 제목", CONTENT, SourceType.ARTICLE));
        for (int i = 1; i <= 3; i++) {
            islandRepository.save(new Island("섬" + i, new float[] {1.0f, 0.0f, 0.0f}));
        }

        List<String> rows = new ArrayList<>();
        rows.add(row("0. 정상 (기준선)", Map.of()));
        rows.add(row("1. 요약 단계 500", Map.of(SUMMARY, ERROR_500)));
        rows.add(row("2. 임베딩 단계 500", Map.of(EMBEDDING, ERROR_500)));
        rows.add(row("3. 추천 판정 단계 500", Map.of(JUDGE, ERROR_500)));
        rows.add(row("4. 요약 단계 429 지속", Map.of(SUMMARY, ERROR_429)));
        rows.add(row("5. 요약 단계 503 한 번", Map.of(SUMMARY, ERROR_503_ONCE)));
        rows.add(row("6. 요약 단계 응답 없음", Map.of(SUMMARY, HANG)));
        rows.add(row("7. 추천 판정 단계 응답 없음", Map.of(JUDGE, HANG)));

        System.out.println("\n===== OPENAI FAILURE MEASURE =====");
        System.out.println("시나리오 | 결과 | 소요(ms) | 스크랩 저장됨 | 사용 중 DB 커넥션 | OpenAI 호출 수");
        rows.forEach(System.out::println);
        System.out.println("==================================\n");
    }

    private String row(String name, Map<Stage, Behavior> setup) throws Exception {
        stub.reset(setup);
        scrapRepository.deleteAll();

        ExecutorService caller = Executors.newSingleThreadExecutor();
        long start = System.nanoTime();
        Future<ScrapCreateResponse> future = caller.submit(() -> scrapService.createScrap(URL, null));

        String outcome;
        String elapsed;
        boolean saved;
        int activeConnections;
        String calls;
        try {
            ScrapCreateResponse response = future.get(HANG_CAP_SECONDS, TimeUnit.SECONDS);
            elapsed = String.valueOf(elapsedMillis(start));
            outcome = "성공 (추천 %d건)".formatted(response.recommendations().size());
        } catch (TimeoutException e) {
            elapsed = ">" + HANG_CAP_SECONDS * 1000;
            outcome = HANG_CAP_SECONDS + "초 동안 끝나지 않음";
        } catch (ExecutionException e) {
            elapsed = String.valueOf(elapsedMillis(start));
            Throwable cause = e.getCause();
            outcome = "실패: " + cause.getClass().getSimpleName();
        }
        // 무응답이면 가짜 서버를 풀기 전(=아직 멈춰 있는 시점)의 상태를 기록한다
        saved = scrapRepository.count() > 0;
        activeConnections = activeConnections();
        calls = stub.callSummary();

        stub.releaseHung();
        try {
            future.get(30, TimeUnit.SECONDS);
        } catch (ExecutionException | TimeoutException ignored) {
            // 정리 단계 - 결과는 위에서 이미 기록함
        }
        caller.shutdownNow();

        return "%s | %s | %s | %s | %d | %s".formatted(name, outcome, elapsed, saved ? "Y" : "N", activeConnections, calls);
    }

    private int activeConnections() throws Exception {
        return dataSource.unwrap(HikariDataSource.class).getHikariPoolMXBean().getActiveConnections();
    }

    private void assertConnectedToInMemoryH2() throws Exception {
        try (Connection connection = dataSource.getConnection()) {
            assertThat(connection.getMetaData().getURL())
                .as("측정은 반드시 테스트용 H2 인메모리 DB에서만 - 실제 DB 보호")
                .startsWith("jdbc:h2:mem:");
        }
    }

    private static long elapsedMillis(long startNanos) {
        return TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - startNanos);
    }
}
