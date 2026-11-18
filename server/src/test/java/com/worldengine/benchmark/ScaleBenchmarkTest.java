package com.worldengine.benchmark;

import static com.worldengine.benchmark.BenchmarkDataSeeder.measure;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

import com.worldengine.island.repository.IslandRepository;
import com.worldengine.island.service.IslandEmbeddingService;
import com.worldengine.recommendation.client.LlmPairwiseJudgeClient;
import com.worldengine.recommendation.service.IslandRecallService;
import com.worldengine.recommendation.service.RecommendationService;
import com.worldengine.scrap.repository.ScrapRepository;
import java.sql.Connection;
import java.util.ArrayList;
import java.util.List;
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
 * - 가짜 데이터는 BenchmarkDataSeeder 참고. 질의 벡터 = 가장 큰 섬의 벡터라 그 섬이 항상 후보에
 *   들어가는 최악 조건.
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

    private static final int[][] SCALES = {{1_000, 10}, {10_000, 30}, {50_000, 100}};

    @Autowired DataSource dataSource;
    @Autowired JdbcTemplate jdbc;
    @Autowired IslandRepository islandRepository;
    @Autowired ScrapRepository scrapRepository;
    @Autowired IslandRecallService islandRecallService;
    @Autowired RecommendationService recommendationService;
    @Autowired IslandEmbeddingService islandEmbeddingService;

    @MockitoBean LlmPairwiseJudgeClient llmPairwiseJudgeClient;

    @Test
    void measureRecommendationPathAtScale() throws Exception {
        assertConnectedToBenchmarkContainer(dataSource, postgres);
        when(llmPairwiseJudgeClient.score(anyString(), anyString())).thenReturn(0.5);
        BenchmarkDataSeeder seeder = new BenchmarkDataSeeder(jdbc, islandRepository);

        List<String> report = new ArrayList<>();
        report.add("scraps | islands | largestIsland | recall | recommend(no LLM) | refresh(largest) | findByUrl   (median/max ms, 10회)");
        for (int[] scale : SCALES) {
            report.add(runScale(seeder, scale[0], scale[1]));
        }
        System.out.println("\n===== SCALE BENCHMARK =====");
        report.forEach(System.out::println);
        System.out.println("===========================\n");
    }

    static void assertConnectedToBenchmarkContainer(DataSource dataSource, PostgreSQLContainer container) throws Exception {
        try (Connection connection = dataSource.getConnection()) {
            String url = connection.getMetaData().getURL();
            assertThat(url)
                .as("측정은 반드시 Testcontainers 전용 DB에서만 - 실제 DB 보호")
                .contains(":" + container.getMappedPort(5432) + "/" + container.getDatabaseName());
        }
    }

    private String runScale(BenchmarkDataSeeder seeder, int scrapCount, int islandCount) {
        BenchmarkDataSeeder.Seeded seeded = seeder.seed(scrapCount, islandCount);
        Long largestIslandId = seeded.largestIslandId();

        float[] query = islandRepository.findById(largestIslandId).orElseThrow().getEmbedding();
        String existingUrl = BenchmarkDataSeeder.URL_PREFIX + (scrapCount / 2);

        String recall = measure(() -> islandRecallService.recall(query, 3));
        String recommend = measure(() -> recommendationService.recommend("요약", query, 3));
        String refresh = measure(() -> {
            islandEmbeddingService.refresh(largestIslandId);
            return null;
        });
        String findByUrl = measure(() -> scrapRepository.findByUrl(existingUrl));

        return String.format("%6d | %7d | %13d | %s | %s | %s | %s",
            scrapCount, islandCount, seeded.largestCount(), recall, recommend, refresh, findByUrl);
    }
}
