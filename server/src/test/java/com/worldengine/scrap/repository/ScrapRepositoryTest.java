package com.worldengine.scrap.repository;

import static org.assertj.core.api.Assertions.assertThat;

import com.worldengine.extraction.model.FallbackLevel;
import com.worldengine.extraction.model.SourceType;
import com.worldengine.scrap.entity.Scrap;
import java.util.List;
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

    @Test
    void findsMemberVectorsOfIslandExcludingScrapsWithoutEmbedding() {
        Scrap withEmbedding = new Scrap("https://example.com/a", "제목A", "본문A", "요약A",
            SourceType.ARTICLE, FallbackLevel.DIRECT_EXTRACTION, null, new float[]{0.1f, 0.2f});
        withEmbedding.confirmIsland(1L);
        Scrap withoutEmbedding = new Scrap("https://example.com/b", null, null, null,
            SourceType.UNKNOWN, FallbackLevel.EXTRACTION_FAILED, null, null);
        withoutEmbedding.confirmIsland(1L);
        Scrap otherIsland = new Scrap("https://example.com/c", "제목C", "본문C", "요약C",
            SourceType.ARTICLE, FallbackLevel.DIRECT_EXTRACTION, null, new float[]{0.3f, 0.4f});
        otherIsland.confirmIsland(2L);
        scrapRepository.saveAll(List.of(withEmbedding, withoutEmbedding, otherIsland));

        List<IslandMemberVector> members = scrapRepository.findMemberVectorsByIslandId(1L);

        assertThat(members).hasSize(1);
        assertThat(members.get(0).id()).isEqualTo(withEmbedding.getId());
        assertThat(members.get(0).summary()).isEqualTo("요약A");
        assertThat(members.get(0).embedding()).containsExactly(0.1f, 0.2f);
    }
}
