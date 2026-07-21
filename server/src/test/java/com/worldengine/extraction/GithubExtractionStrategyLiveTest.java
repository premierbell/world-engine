package com.worldengine.extraction;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.worldengine.extraction.model.ExtractionResult;
import com.worldengine.extraction.model.ExtractionStatus;
import com.worldengine.extraction.strategy.GithubExtractionStrategy;
import java.net.URI;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

/**
 * 실제 GitHub 저장소 URL로 README API 호출을 검증한다. 인증 없는
 * API는 시간당 60회 제한이 있으니 표본을 적게 유지한다.
 */
@Tag("live")
class GithubExtractionStrategyLiveTest {

    private final GithubExtractionStrategy strategy = new GithubExtractionStrategy();

    @ParameterizedTest
    @ValueSource(strings = {
        "https://github.com/spring-projects/spring-boot",
        "https://github.com/spring-projects/spring-boot/tree/main",
    })
    void extractsReadmeFromGithubRepository(String url) {
        ExtractionResult result = strategy.extract(URI.create(url));

        assertTrue(result.status() == ExtractionStatus.SUCCESS || result.status() == ExtractionStatus.PARTIAL,
            "expected SUCCESS or PARTIAL but got " + result.status() + " (" + result.failureReason() + ")");
        assertFalse(result.content() == null || result.content().isBlank());
    }
}
