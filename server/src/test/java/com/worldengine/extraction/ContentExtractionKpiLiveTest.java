package com.worldengine.extraction;

import static org.junit.jupiter.api.Assertions.assertFalse;

import com.worldengine.extraction.model.ExtractionResult;
import com.worldengine.extraction.model.FailureReason;
import com.worldengine.extraction.model.FallbackLevel;
import com.worldengine.extraction.model.SourceType;
import com.worldengine.extraction.service.ContentExtractionService;
import com.worldengine.extraction.strategy.ArticleExtractionStrategy;
import com.worldengine.extraction.strategy.GithubExtractionStrategy;
import com.worldengine.extraction.strategy.NaverBlogExtractionStrategy;
import com.worldengine.extraction.strategy.PdfExtractionStrategy;
import com.worldengine.extraction.strategy.YouTubeExtractionStrategy;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/**
 * Round 1의 실제 스크랩 URL 25개로 ContentExtractionService 전체(5개
 * 전략)를 재현해서 docs/content_extraction.md의 KPI(Success Rate 등)를
 * 실측한다. round1.json은 개인 데이터라 .gitignore 대상 - 로컬에 파일이
 * 없으면 이 테스트는 건너뛴다.
 */
@Tag("live")
class ContentExtractionKpiLiveTest {

    private static final String ROUND1_PATH = "../experiments/real_user_organization/round1.json";

    @Test
    void measuresSuccessRateAgainstRound1Urls() throws IOException {
        File file = new File(ROUND1_PATH);
        if (!file.exists()) {
            System.out.println("round1.json 없음 - KPI 측정 스킵");
            return;
        }

        ContentExtractionService service = new ContentExtractionService(List.of(
            new NaverBlogExtractionStrategy(),
            new GithubExtractionStrategy(),
            new YouTubeExtractionStrategy(),
            new PdfExtractionStrategy(),
            new ArticleExtractionStrategy()
        ));

        ObjectMapper mapper = new ObjectMapper();
        JsonNode root = mapper.readTree(file);
        JsonNode scraps = root.path("scraps");

        List<ExtractionResult> results = new ArrayList<>();
        for (JsonNode scrap : scraps) {
            String url = scrap.path("url").asString(null);
            if (url == null || url.isBlank()) {
                continue;
            }
            results.add(service.extract(url));
        }

        printReport(results);
        assertFalse(results.isEmpty());
    }

    private void printReport(List<ExtractionResult> results) {
        int total = results.size();
        long successOrPartial = results.stream()
            .filter(r -> r.fallbackLevel().level() <= FallbackLevel.OPEN_GRAPH_ONLY.level())
            .count();

        System.out.printf("%n=== Content Extraction KPI (N=%d) ===%n", total);
        System.out.printf("Success Rate (DIRECT+OPEN_GRAPH): %.1f%%%n", 100.0 * successOrPartial / total);

        Map<FallbackLevel, Long> byLevel = new EnumMap<>(FallbackLevel.class);
        for (ExtractionResult r : results) {
            byLevel.merge(r.fallbackLevel(), 1L, Long::sum);
        }
        System.out.println("-- Fallback Distribution --");
        for (FallbackLevel level : FallbackLevel.values()) {
            long count = byLevel.getOrDefault(level, 0L);
            System.out.printf("  %-20s %d (%.1f%%)%n", level, count, 100.0 * count / total);
        }

        Map<SourceType, List<ExtractionResult>> bySource = new EnumMap<>(SourceType.class);
        for (ExtractionResult r : results) {
            bySource.computeIfAbsent(r.sourceType(), k -> new ArrayList<>()).add(r);
        }
        System.out.println("-- SourceType Distribution / Strategy Hit Rate (같은 값 - 전략 1개당 SourceType 1개) --");
        for (var entry : bySource.entrySet()) {
            long ok = entry.getValue().stream()
                .filter(r -> r.fallbackLevel().level() <= FallbackLevel.OPEN_GRAPH_ONLY.level())
                .count();
            System.out.printf("  %-15s %d/%d hit, success %d/%d%n",
                entry.getKey(), entry.getValue().size(), total, ok, entry.getValue().size());
        }

        Map<FailureReason, Long> byReason = new EnumMap<>(FailureReason.class);
        for (ExtractionResult r : results) {
            byReason.merge(r.failureReason(), 1L, Long::sum);
        }
        System.out.println("-- Failure Reasons --");
        for (var entry : byReason.entrySet()) {
            System.out.printf("  %-20s %d%n", entry.getKey(), entry.getValue());
        }

        double avgLength = results.stream()
            .filter(r -> r.fallbackLevel() == FallbackLevel.DIRECT_EXTRACTION)
            .mapToInt(r -> r.content() == null ? 0 : r.content().length())
            .average()
            .orElse(0);
        System.out.printf("Average Content Length (DIRECT_EXTRACTION only): %.0f chars%n", avgLength);
    }

}
