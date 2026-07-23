package com.worldengine.scrap.repository;

import static org.assertj.core.api.Assertions.assertThat;

import com.worldengine.extraction.model.FallbackLevel;
import com.worldengine.extraction.model.SourceType;
import com.worldengine.scrap.entity.Scrap;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.data.jpa.test.autoconfigure.DataJpaTest;

@DataJpaTest
class ScrapRepositoryTest {

    @Autowired
    private ScrapRepository scrapRepository;

    @Test
    void savesAndLoadsScrapWithEmbedding() {
        float[] embedding = {0.1f, 0.2f, 0.3f};
        Scrap scrap = new Scrap(
            "https://example.com/article",
            "제목",
            "본문 내용",
            "요약",
            SourceType.ARTICLE,
            FallbackLevel.DIRECT_EXTRACTION,
            "나중에 다시 읽으려고",
            embedding
        );

        Scrap saved = scrapRepository.save(scrap);
        Scrap found = scrapRepository.findById(saved.getId()).orElseThrow();

        assertThat(found.getUrl()).isEqualTo("https://example.com/article");
        assertThat(found.getSourceType()).isEqualTo(SourceType.ARTICLE);
        assertThat(found.getFallbackLevel()).isEqualTo(FallbackLevel.DIRECT_EXTRACTION);
        assertThat(found.getEmbedding()).containsExactly(embedding);
    }

    @Test
    void savesScrapWithoutEmbeddingWhenExtractionFailed() {
        Scrap scrap = new Scrap(
            "https://example.com/failed",
            null, null, null,
            SourceType.UNKNOWN,
            FallbackLevel.EXTRACTION_FAILED,
            null,
            null
        );

        Scrap saved = scrapRepository.save(scrap);
        Scrap found = scrapRepository.findById(saved.getId()).orElseThrow();

        assertThat(found.getEmbedding()).isNull();
        assertThat(found.getTitle()).isNull();
    }
}
