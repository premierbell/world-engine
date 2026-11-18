package com.worldengine.benchmark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

import com.worldengine.common.jpa.EmbeddingConverter;
import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.island.service.IslandEmbeddingService;
import com.worldengine.recommendation.client.LlmPairwiseJudgeClient;
import com.worldengine.recommendation.service.IslandRecallService;
import com.worldengine.recommendation.service.RecommendationService;
import com.worldengine.scrap.repository.ScrapRepository;
import java.sql.Connection;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Random;
import java.util.function.Supplier;
import javax.sql.DataSource;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;

/**
 * [측정 도구] 스크랩이 늘어날 때 추천 경로 중 어디가 먼저 느려지는지 잰다 (2026-11-18, 측정 ②).
 *
 * - 측정 전용 Postgres를 Testcontainers로 새로 띄운다. 실제 DB에는 접근하지 않으며, 시작 시
 *   연결된 DB가 이 컨테이너인지 확인하고 아니면 즉시 실패한다.
 * - LLM은 Mock(즉시 0.5 반환) - LLM 시간(병렬 약 0.7초)은 별도 측정됨. 여기서는 그 위에 얹히는
 *   DB/계산 비용만 본다.
 * - 가짜 데이터 크기는 실제 평균에 맞춤: 본문 약 7,650자, 임베딩 1536차원(TEXT 약 19KB).
 *   한 섬에 40%가 몰리는 분포(실제: 82건 중 35건이 한 섬). 질의 벡터 = 가장 큰 섬의 벡터라
 *   그 섬이 항상 후보에 들어가는 최악 조건.
 *
 * 사전 고정한 판단 기준: 어떤 지점이 1회 호출에 200ms 이상이면 그 규모에서 개선 필요.
 * Recall이면 벡터 인덱스(pgvector) 검토, 대표 텍스트/중복 검사면 쿼리 개선으로 해결.
 *
 * 실행: ./gradlew benchmarkTest (기본 test에서는 제외)
 */
@Tag("benchmark")
@Testcontainers
@SpringBootTest(properties = {
    "spring.datasource.driver-class-name=org.postgresql.Driver",
    "spring.jpa.hibernate.ddl-auto=create-drop"
})
class ScaleBenchmarkTest {

    @Container
    @ServiceConnection
    static PostgreSQLContainer postgres = new PostgreSQLContainer(DockerImageName.parse("postgres:16"));

    private static final int DIM = 1536;
    private static final int CONTENT_LENGTH = 7650;
    private static final int WARMUP = 3;
    private static final int RUNS = 10;
    private static final int[][] SCALES = {{1_000, 10}, {10_000, 30}, {50_000, 100}};

    @Autowired DataSource dataSource;
    @Autowired JdbcTemplate jdbc;
    @Autowired IslandRepository islandRepository;
    @Autowired ScrapRepository scrapRepository;
    @Autowired IslandRecallService islandRecallService;
    @Autowired RecommendationService recommendationService;
    @Autowired IslandEmbeddingService islandEmbeddingService;

    @MockitoBean LlmPairwiseJudgeClient llmPairwiseJudgeClient;

    private final Random random = new Random(42);
    private final EmbeddingConverter converter = new EmbeddingConverter();

    @Test
    void measureRecommendationPathAtScale() throws Exception {
        assertConnectedToBenchmarkContainer();
        when(llmPairwiseJudgeClient.score(anyString(), anyString())).thenReturn(0.5);

        List<String> report = new ArrayList<>();
        report.add("scraps | islands | largestIsland | recall | recommend(no LLM) | refresh(largest) | findByUrl   (median/max ms, 10회)");
        for (int[] scale : SCALES) {
            report.add(runScale(scale[0], scale[1]));
        }
        System.out.println("\n===== SCALE BENCHMARK =====");
        report.forEach(System.out::println);
        System.out.println("===========================\n");
    }

    private void assertConnectedToBenchmarkContainer() throws Exception {
        try (Connection connection = dataSource.getConnection()) {
            String url = connection.getMetaData().getURL();
            assertThat(url)
                .as("측정은 반드시 Testcontainers 전용 DB에서만 - 실제 DB 보호")
                .contains(":" + postgres.getMappedPort(5432) + "/" + postgres.getDatabaseName());
        }
    }

    private String runScale(int scrapCount, int islandCount) {
        jdbc.execute("TRUNCATE TABLE scrap, island, topic RESTART IDENTITY CASCADE");

        List<Long> islandIds = new ArrayList<>();
        for (int i = 0; i < islandCount; i++) {
            islandIds.add(islandRepository.save(new Island("섬" + i, randomEmbedding())).getId());
        }
        Long largestIslandId = islandIds.get(0);
        int largestCount = seedScraps(scrapCount, islandIds);

        float[] query = islandRepository.findById(largestIslandId).orElseThrow().getEmbedding();
        String existingUrl = "https://bench.example.com/scrap/" + (scrapCount / 2);

        String recall = measure(() -> islandRecallService.recall(query, 3));
        String recommend = measure(() -> recommendationService.recommend("요약", query, 3));
        String refresh = measure(() -> {
            islandEmbeddingService.refresh(largestIslandId);
            return null;
        });
        String findByUrl = measure(() -> scrapRepository.findByUrl(existingUrl));

        return String.format("%6d | %7d | %13d | %s | %s | %s | %s",
            scrapCount, islandCount, largestCount, recall, recommend, refresh, findByUrl);
    }

    /** JPA saveAll 대신 JDBC 배치로 넣는다 - 5만 건 x 약 27KB를 빠르게 넣기 위해. 가장 큰 섬 멤버 수를 반환. */
    private int seedScraps(int scrapCount, List<Long> islandIds) {
        List<String> embeddingPool = new ArrayList<>();
        List<String> contentPool = new ArrayList<>();
        for (int i = 0; i < 200; i++) {
            embeddingPool.add(converter.convertToDatabaseColumn(randomEmbedding()));
            contentPool.add(randomText(CONTENT_LENGTH));
        }
        String summary = randomText(245);

        String sql = "INSERT INTO scrap (url, title, content, summary, source_type, fallback_level, "
            + "embedding, created_at, island_id) VALUES (?, ?, ?, ?, 'ARTICLE', 'DIRECT_EXTRACTION', ?, ?, ?)";
        int largest = 0;
        List<Object[]> batch = new ArrayList<>();
        for (int i = 0; i < scrapCount; i++) {
            Long islandId = random.nextDouble() < 0.4
                ? islandIds.get(0)
                : islandIds.get(1 + random.nextInt(islandIds.size() - 1));
            if (islandId.equals(islandIds.get(0))) {
                largest++;
            }
            batch.add(new Object[]{
                "https://bench.example.com/scrap/" + i, "제목 " + i,
                contentPool.get(i % contentPool.size()), summary,
                embeddingPool.get(i % embeddingPool.size()), Timestamp.from(Instant.now()), islandId});
            if (batch.size() == 500) {
                jdbc.batchUpdate(sql, batch);
                batch.clear();
            }
        }
        if (!batch.isEmpty()) {
            jdbc.batchUpdate(sql, batch);
        }
        jdbc.execute("ANALYZE scrap");
        return largest;
    }

    private String measure(Supplier<?> action) {
        for (int i = 0; i < WARMUP; i++) {
            action.get();
        }
        long[] millis = new long[RUNS];
        for (int i = 0; i < RUNS; i++) {
            long start = System.nanoTime();
            action.get();
            millis[i] = (System.nanoTime() - start) / 1_000_000;
        }
        Arrays.sort(millis);
        return String.format("%5d / %5d", millis[RUNS / 2], millis[RUNS - 1]);
    }

    private float[] randomEmbedding() {
        float[] vector = new float[DIM];
        for (int i = 0; i < DIM; i++) {
            vector[i] = (float) random.nextGaussian() * 0.03f;
        }
        return vector;
    }

    private String randomText(int length) {
        String alphabet = "가나다라마바사아자차카타파하 abcdefghij ";
        StringBuilder builder = new StringBuilder(length);
        for (int i = 0; i < length; i++) {
            builder.append(alphabet.charAt(random.nextInt(alphabet.length())));
        }
        return builder.toString();
    }
}
