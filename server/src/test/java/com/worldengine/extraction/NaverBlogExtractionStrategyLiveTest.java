package com.worldengine.extraction;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.worldengine.extraction.model.ExtractionResult;
import com.worldengine.extraction.model.ExtractionStatus;
import com.worldengine.extraction.strategy.NaverBlogExtractionStrategy;
import java.net.URI;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

/**
 * 실제 네이버 블로그 URL로 PostView.naver 2단계 요청 + se-main-container
 * 파싱을 검증한다. Round 1에서는 이 URL들이 전부 WebFetch로 직접 추출
 * 실패했었다 - NaverBlogExtractionStrategy가 그 실패를 해결하는지 확인.
 */
@Tag("live")
class NaverBlogExtractionStrategyLiveTest {

    private final NaverBlogExtractionStrategy strategy = new NaverBlogExtractionStrategy();

    @ParameterizedTest
    @ValueSource(strings = {
        "https://blog.naver.com/dailytrip_/222858904869",
        "https://blog.naver.com/nimo611/223347108051",
        "https://blog.naver.com/happy_snubh/223529460665",
    })
    void extractsMainContentFromNaverBlogPosts(String url) {
        ExtractionResult result = strategy.extract(URI.create(url));

        assertTrue(
            result.status() == ExtractionStatus.SUCCESS || result.status() == ExtractionStatus.PARTIAL,
            "expected SUCCESS or PARTIAL but got " + result.status() + " (" + result.failureReason() + ")"
        );
        assertFalse(result.content() == null || result.content().isBlank());
    }
}
