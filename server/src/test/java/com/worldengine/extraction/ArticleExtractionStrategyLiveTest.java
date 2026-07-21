package com.worldengine.extraction;

import com.worldengine.extraction.model.ExtractionResult;
import com.worldengine.extraction.model.ExtractionStatus;
import com.worldengine.extraction.strategy.ArticleExtractionStrategy;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.net.URI;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 실제 네트워크로 진짜 URL을 가져와서 추출을 검증한다 - 외부 서비스에
 * 의존하므로 기본 `./gradlew test`에서는 제외된다("live" 태그).
 * `./gradlew liveTest`로 수동 실행할 것.
 *
 * docs/content_extraction.md의 품질 지표(Success Rate 등)를 재는
 * 첫 데이터 포인트 - Round 1(WebFetch 기준 36% 성공)과 비교할 근거가
 * 된다.
 */
@Tag("live")
class ArticleExtractionStrategyLiveTest {

    private final ArticleExtractionStrategy strategy = new ArticleExtractionStrategy();

    @ParameterizedTest
    @ValueSource(strings = {
        "https://www.44bits.io/posts/easy-deploy-with-docker/",
        "https://en.wikipedia.org/wiki/Spring_Framework",
    })
    void extractsMainContentFromStaticArticlePages(String url) {
        ExtractionResult result = strategy.extract(URI.create(url));

        assertTrue(
            result.status() == ExtractionStatus.SUCCESS || result.status() == ExtractionStatus.PARTIAL,
            "expected SUCCESS or PARTIAL but got " + result.status() + " (" + result.failureReason() + ")"
        );
        assertFalse(result.content() == null || result.content().isBlank());
        assertFalse(result.title() == null || result.title().isBlank());
    }
}
