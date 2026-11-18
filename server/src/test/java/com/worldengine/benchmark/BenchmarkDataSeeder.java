package com.worldengine.benchmark;

import com.worldengine.common.jpa.EmbeddingConverter;
import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Random;
import java.util.function.Supplier;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * [측정 도구] 벤치마크용 가짜 데이터 생성/시간 측정 공용 헬퍼.
 * 데이터 크기는 실제 평균에 맞춤: 본문 약 7,650자, 임베딩 1536차원(TEXT 약 19KB),
 * 한 섬에 40%가 몰리는 분포(실제 82건 중 35건이 한 섬).
 */
class BenchmarkDataSeeder {

    static final int DIM = 1536;
    static final int CONTENT_LENGTH = 7650;
    static final String URL_PREFIX = "https://bench.example.com/scrap/";

    private final JdbcTemplate jdbc;
    private final IslandRepository islandRepository;
    private final Random random = new Random(42);
    private final EmbeddingConverter converter = new EmbeddingConverter();

    BenchmarkDataSeeder(JdbcTemplate jdbc, IslandRepository islandRepository) {
        this.jdbc = jdbc;
        this.islandRepository = islandRepository;
    }

    record Seeded(List<Long> islandIds, Long largestIslandId, int largestCount) {}

    Seeded seed(int scrapCount, int islandCount) {
        jdbc.execute("TRUNCATE TABLE scrap, island, topic RESTART IDENTITY CASCADE");

        List<Long> islandIds = new ArrayList<>();
        for (int i = 0; i < islandCount; i++) {
            islandIds.add(islandRepository.save(new Island("섬" + i, randomEmbedding())).getId());
        }

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
                URL_PREFIX + i, "제목 " + i,
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
        return new Seeded(islandIds, islandIds.get(0), largest);
    }

    /** 워밍업 3회 후 10회 측정, "중앙값 / 최댓값" ms. */
    static String measure(Supplier<?> action) {
        long[] millis = measureMillis(action);
        return String.format("%5d / %5d", millis[millis.length / 2], millis[millis.length - 1]);
    }

    static long medianMillis(Supplier<?> action) {
        long[] millis = measureMillis(action);
        return millis[millis.length / 2];
    }

    private static long[] measureMillis(Supplier<?> action) {
        for (int i = 0; i < 3; i++) {
            action.get();
        }
        long[] millis = new long[10];
        for (int i = 0; i < millis.length; i++) {
            long start = System.nanoTime();
            action.get();
            millis[i] = (System.nanoTime() - start) / 1_000_000;
        }
        Arrays.sort(millis);
        return millis;
    }

    float[] randomEmbedding() {
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
