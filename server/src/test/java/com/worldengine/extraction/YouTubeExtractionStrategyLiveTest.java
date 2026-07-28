package com.worldengine.extraction;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.worldengine.extraction.model.ExtractionResult;
import com.worldengine.extraction.model.ExtractionStatus;
import com.worldengine.extraction.service.ExtractionQualityEvaluator;
import com.worldengine.extraction.strategy.YouTubeExtractionStrategy;
import java.net.URI;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

/**
 * 실제 YouTube URL(watch, youtu.be 단축링크 둘 다) 대상 검증.
 */
@Tag("live")
class YouTubeExtractionStrategyLiveTest {

    private final YouTubeExtractionStrategy strategy = new YouTubeExtractionStrategy(new ExtractionQualityEvaluator(50));

    @ParameterizedTest
    @ValueSource(strings = {
        "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        "https://youtu.be/jNQXAC9IVRw",
    })
    void extractsTitleAndDescriptionFromYoutubeVideo(String url) {
        ExtractionResult result = strategy.extract(URI.create(url));

        assertTrue(
            result.status() == ExtractionStatus.SUCCESS
                || result.status() == ExtractionStatus.PARTIAL,
            "expected SUCCESS or PARTIAL but got " + result.status() + " (" + result.failureReason()
                + ")"
        );
        assertFalse(result.content() == null || result.content().isBlank());
        assertFalse(result.title() == null || result.title().isBlank());
    }
}
