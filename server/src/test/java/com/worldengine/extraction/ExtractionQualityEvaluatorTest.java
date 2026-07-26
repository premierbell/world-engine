package com.worldengine.extraction;

import static org.assertj.core.api.Assertions.assertThat;

import com.worldengine.extraction.service.ExtractionQualityEvaluator;
import org.junit.jupiter.api.Test;

class ExtractionQualityEvaluatorTest {

    private final ExtractionQualityEvaluator evaluator = new ExtractionQualityEvaluator(50);

    @Test
    void rejectsNullContent() {
        assertThat(evaluator.isValid(null)).isFalse();
    }

    @Test
    void rejectsContentShorterThanMinLength() {
        assertThat(evaluator.isValid("국내최초 취업정보회사 - 제로베이스")).isFalse();
    }

    @Test
    void acceptsContentAtOrAboveMinLength() {
        String content = "가".repeat(50);
        assertThat(evaluator.isValid(content)).isTrue();
    }
}
