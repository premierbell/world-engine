package com.worldengine.benchmark;

import static com.worldengine.benchmark.BenchmarkDataSeeder.medianMillis;

import com.worldengine.common.jpa.EmbeddingConverter;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.recommendation.vector.CosineSimilarity;
import com.worldengine.scrap.repository.ScrapRepository;
import java.util.List;
import javax.sql.DataSource;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.jdbc.core.JdbcTemplate;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;

/**
 * [측정 도구] 섬 멤버를 읽는 비용(측정 ②에서 멤버 1건당 약 0.4ms)이 어디서 나오는지 쪼갠다.
 * 스크랩 1만 건(가장 큰 섬 약 4,000건)에서 가장 큰 섬 멤버를 읽는 비용을 단계별로 측정.
 *
 * ① JPA findByIslandId (지금 refresh/대표 텍스트가 하는 일: 전체 컬럼 + 임베딩 파싱)
 * ② JDBC id만                      → 쿼리 자체
 * ③ JDBC id·summary·embedding 텍스트 (파싱 없음) → 임베딩 전송
 * ④ JDBC 모든 컬럼 텍스트 (파싱 없음)          → ④ - ③ = 본문 전송
 * ⑤ 메모리의 임베딩 텍스트 → float[] 파싱만    → 파싱
 * ⑥ 파싱된 벡터로 평균 + cosine 계산만         → 계산
 *
 * 사전 고정한 선택 기준:
 * - 본문 전송(④-③)이 ①의 절반 이상 → 필요한 컬럼만 조회(projection)
 * - 임베딩 파싱(⑤)이 ①의 절반 이상 → 파싱을 줄이는 방향(증분 갱신, 저장 형식 변경)
 * - 둘 다 크면 둘 다 적용하고 효과를 각각 측정
 *
 * 실행: ./gradlew benchmarkTest --tests '*MemberCostBreakdownBenchmarkTest'
 */
@Tag("benchmark")
@Testcontainers
@SpringBootTest(properties = {
    "spring.datasource.driver-class-name=org.postgresql.Driver",
    "spring.jpa.hibernate.ddl-auto=create-drop"
})
class MemberCostBreakdownBenchmarkTest {

    @Container
    @ServiceConnection
    static PostgreSQLContainer postgres = new PostgreSQLContainer(DockerImageName.parse("postgres:16"));

    @Autowired DataSource dataSource;
    @Autowired JdbcTemplate jdbc;
    @Autowired IslandRepository islandRepository;
    @Autowired ScrapRepository scrapRepository;

    private final EmbeddingConverter converter = new EmbeddingConverter();

    @Test
    void breakDownMemberLoadingCost() throws Exception {
        ScaleBenchmarkTest.assertConnectedToBenchmarkContainer(dataSource, postgres);
        BenchmarkDataSeeder seeder = new BenchmarkDataSeeder(jdbc, islandRepository);
        BenchmarkDataSeeder.Seeded seeded = seeder.seed(10_000, 30);
        Long islandId = seeded.largestIslandId();
        float[] query = seeder.randomEmbedding();

        long jpaFull = medianMillis(() -> scrapRepository.findByIslandId(islandId));
        long idOnly = medianMillis(() -> jdbc.queryForList(
            "SELECT id FROM scrap WHERE island_id = ?", Long.class, islandId));
        long embeddingText = medianMillis(() -> jdbc.queryForList(
            "SELECT id, summary, embedding FROM scrap WHERE island_id = ?", islandId));
        long allColumnsText = medianMillis(() -> jdbc.queryForList(
            "SELECT * FROM scrap WHERE island_id = ?", islandId));

        List<String> embeddingStrings = jdbc.queryForList(
            "SELECT embedding FROM scrap WHERE island_id = ?", String.class, islandId);
        long parseOnly = medianMillis(() -> embeddingStrings.stream()
            .map(converter::convertToEntityAttribute).toList());

        List<float[]> vectors = embeddingStrings.stream().map(converter::convertToEntityAttribute).toList();
        long computeOnly = medianMillis(() -> {
            double[] sum = new double[BenchmarkDataSeeder.DIM];
            double best = -1;
            for (float[] vector : vectors) {
                for (int i = 0; i < vector.length; i++) {
                    sum[i] += vector[i];
                }
                best = Math.max(best, CosineSimilarity.similarity(query, vector));
            }
            return best;
        });

        System.out.println("\n===== MEMBER COST BREAKDOWN (median ms, 10회) =====");
        System.out.printf("members in largest island        : %d%n", seeded.largestCount());
        System.out.printf("① JPA findByIslandId (current)  : %d%n", jpaFull);
        System.out.printf("② JDBC id only                  : %d%n", idOnly);
        System.out.printf("③ JDBC id+summary+embedding text: %d%n", embeddingText);
        System.out.printf("④ JDBC all columns text         : %d   (④-③ content transfer ≈ %d)%n",
            allColumnsText, allColumnsText - embeddingText);
        System.out.printf("⑤ parse embedding JSON only     : %d%n", parseOnly);
        System.out.printf("⑥ mean + cosine compute only    : %d%n", computeOnly);
        System.out.println("=================================================\n");
    }
}
