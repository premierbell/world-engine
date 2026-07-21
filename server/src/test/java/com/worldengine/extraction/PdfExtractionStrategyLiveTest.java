package com.worldengine.extraction;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.worldengine.extraction.model.ExtractionResult;
import com.worldengine.extraction.model.ExtractionStatus;
import com.worldengine.extraction.strategy.PdfExtractionStrategy;
import java.net.URI;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * 실제 PDF URL로 텍스트 레이어 추출을 검증한다.
 */
@Tag("live")
class PdfExtractionStrategyLiveTest {

    private final PdfExtractionStrategy strategy = new PdfExtractionStrategy();

    @Test
    void extractsTextFromPdf() {
        ExtractionResult result = strategy.extract(
            URI.create("https://www.orimi.com/pdf-test.pdf"));
        assertTrue(
            result.status() == ExtractionStatus.SUCCESS || result.status() == ExtractionStatus.PARTIAL,
            "expected SUCCESS or PARTIAL but got " + result.status() + " (" + result.failureReason() + ")");
        assertFalse(result.content() == null || result.content().isBlank());
    }
}
