package com.worldengine.scrap.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.worldengine.extraction.model.ExtractionResult;
import com.worldengine.extraction.model.ExtractionStatus;
import com.worldengine.extraction.model.FailureReason;
import com.worldengine.extraction.model.FallbackLevel;
import com.worldengine.extraction.model.SourceType;
import com.worldengine.extraction.service.ContentExtractionService;
import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.recommendation.client.ContentSummaryClient;
import com.worldengine.recommendation.client.OpenAiEmbeddingClient;
import com.worldengine.recommendation.service.IslandRecommendation;
import com.worldengine.recommendation.service.RecommendationService;
import com.worldengine.scrap.dto.ScrapCreateResponse;
import com.worldengine.scrap.entity.Scrap;
import com.worldengine.scrap.repository.ScrapRepository;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
public class ScrapServiceTest {

    @Mock
    private ContentExtractionService contentExtractionService;

    @Mock
    private ContentSummaryClient contentSummaryClient;

    @Mock
    private OpenAiEmbeddingClient openAiEmbeddingClient;

    @Mock
    private ScrapRepository scrapRepository;

    @Mock
    private RecommendationService recommendationService;

    @Mock
    private IslandRepository islandRepository;

    @Spy
    private ScrapContentPreprocessor scrapContentPreprocessor = new ScrapContentPreprocessor(2000);

    @InjectMocks
    private ScrapService scrapService;

    @Test
    void createsScrapAndReturnsRecommendationsWhenExtractionSucceeds() {
        ExtractionResult extractionResult = ExtractionResult.success("제목", "본문 내용", SourceType.ARTICLE);
        when(contentExtractionService.extract("https://example.com")).thenReturn(extractionResult);
        when(contentSummaryClient.summarize("본문 내용")).thenReturn("본문 내용");

        float[] embedding = {0.1f, 0.2f};
        when(openAiEmbeddingClient.embed("본문 내용")).thenReturn(embedding);

        Scrap saved = new Scrap("https://example.com", "제목", "본문 내용", "본문 내용",
            SourceType.ARTICLE, FallbackLevel.DIRECT_EXTRACTION, null, embedding);
        ReflectionTestUtils.setField(saved, "id", 1L);
        when(scrapRepository.save(any())).thenReturn(saved);

        List<IslandRecommendation> recommendations = List.of(new IslandRecommendation(1L, "다이어트", 0.8));
        when(recommendationService.recommend("본문 내용", embedding, 3)).thenReturn(recommendations);

        ScrapCreateResponse response = scrapService.createScrap("https://example.com", null);

        assertThat(response.scrapId()).isEqualTo(1L);
        assertThat(response.recommendations()).isEqualTo(recommendations);
    }

    @Test
    void skipsEmbeddingAndRecommendationWhenExtractionFails() {
        ExtractionResult extractionResult = ExtractionResult.failed(SourceType.UNKNOWN, FailureReason.UNSUPPORTED_SOURCE);
        when(contentExtractionService.extract("https://example.com/bad")).thenReturn(extractionResult);

        Scrap saved = new Scrap("https://example.com/bad", null, null, null,
            SourceType.UNKNOWN, FallbackLevel.EXTRACTION_FAILED, null, null);
        ReflectionTestUtils.setField(saved, "id", 2L);
        when(scrapRepository.save(any())).thenReturn(saved);

        ScrapCreateResponse response = scrapService.createScrap("https://example.com/bad", null);

        assertThat(response.recommendations()).isEmpty();
        verify(contentSummaryClient, never()).summarize(any());
        verify(openAiEmbeddingClient, never()).embed(any());
        verify(recommendationService, never()).recommend(any(), any(), anyInt());
    }

    @Test
    void treatsNoContentSummaryAsEmpty() {
        ExtractionResult extractionResult = ExtractionResult.success("제목", "저작권 안내만 있음", SourceType.ARTICLE);
        when(contentExtractionService.extract("https://example.com/boilerplate")).thenReturn(extractionResult);
        when(contentSummaryClient.summarize("저작권 안내만 있음")).thenReturn("NO_CONTENT");

        Scrap saved = new Scrap("https://example.com/boilerplate", "제목", "저작권 안내만 있음", null,
            SourceType.ARTICLE, FallbackLevel.DIRECT_EXTRACTION, null, null);
        ReflectionTestUtils.setField(saved, "id", 12L);
        saved.recordFailureReason(FailureReason.BOILERPLATE_ONLY);
        when(scrapRepository.save(any())).thenReturn(saved);

        ScrapCreateResponse response = scrapService.createScrap("https://example.com/boilerplate", null);

        assertThat(response.recommendations()).isEmpty();
        assertThat(response.status()).isEqualTo(ExtractionStatus.FAILED);
        assertThat(response.failureReason()).isEqualTo(FailureReason.BOILERPLATE_ONLY);
        verify(openAiEmbeddingClient, never()).embed(any());
    }

    @Test
    void refreshesRecommendationsForUnconfirmedScrap() {
        float[] embedding = {0.1f, 0.2f};
        Scrap scrap = new Scrap("https://example.com", "제목", "본문 내용", "본문 내용",
            SourceType.ARTICLE, FallbackLevel.DIRECT_EXTRACTION, null, embedding);
        ReflectionTestUtils.setField(scrap, "id", 1L);
        when(scrapRepository.findById(1L)).thenReturn(Optional.of(scrap));

        List<IslandRecommendation> recommendations = List.of(new IslandRecommendation(2L, "백엔드", 0.7));
        when(recommendationService.recommend("본문 내용", embedding, 3)).thenReturn(recommendations);
        when(scrapRepository.save(any())).thenReturn(scrap);

        List<IslandRecommendation> result = scrapService.refreshRecommendations(1L);

        assertThat(result).isEqualTo(recommendations);
        assertThat(scrap.getRecommendedIslandId()).isEqualTo(2L);
    }

    @Test
    void throwsWhenRefreshingRecommendationsForAlreadyConfirmedScrap() {
        Scrap scrap = new Scrap("https://example.com", "제목", "본문 내용", "본문 내용",
            SourceType.ARTICLE, FallbackLevel.DIRECT_EXTRACTION, null, new float[]{0.1f, 0.2f});
        ReflectionTestUtils.setField(scrap, "id", 1L);
        scrap.confirmIsland(5L);
        when(scrapRepository.findById(1L)).thenReturn(Optional.of(scrap));

        assertThatThrownBy(() -> scrapService.refreshRecommendations(1L))
            .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void returnsDuplicateWithoutCreatingWhenUrlAlreadyExists() {
        Scrap existing = new Scrap("https://example.com", "기존 제목", "본문", "본문",
            SourceType.ARTICLE, FallbackLevel.DIRECT_EXTRACTION, null, new float[]{0.1f});
        ReflectionTestUtils.setField(existing, "id", 10L);
        existing.confirmIsland(3L);
        when(scrapRepository.findByUrl("https://example.com")).thenReturn(Optional.of(existing));
        when(islandRepository.findById(3L)).thenReturn(Optional.of(new Island("여행", new float[]{0.1f})));

        ScrapCreateResponse response = scrapService.createScrap("https://example.com", null);

        assertThat(response.duplicate()).isTrue();
        assertThat(response.scrapId()).isEqualTo(10L);
        assertThat(response.existingIslandId()).isEqualTo(3L);
        assertThat(response.existingIslandName()).isEqualTo("여행");
        verify(contentExtractionService, never()).extract(any());
        verify(scrapRepository, never()).save(any());
    }

    @Test
    void skipsDuplicateCheckWhenForced() {
        ExtractionResult extractionResult = ExtractionResult.success("제목", "본문 내용", SourceType.ARTICLE);
        when(contentExtractionService.extract("https://example.com")).thenReturn(extractionResult);
        when(contentSummaryClient.summarize("본문 내용")).thenReturn("본문 내용");
        float[] embedding = {0.1f, 0.2f};
        when(openAiEmbeddingClient.embed("본문 내용")).thenReturn(embedding);
        Scrap saved = new Scrap("https://example.com", "제목", "본문 내용", "본문 내용",
            SourceType.ARTICLE, FallbackLevel.DIRECT_EXTRACTION, null, embedding);
        ReflectionTestUtils.setField(saved, "id", 11L);
        when(scrapRepository.save(any())).thenReturn(saved);
        when(recommendationService.recommend(any(), any(), anyInt())).thenReturn(List.of());

        ScrapCreateResponse response = scrapService.createScrap("https://example.com", null, true);

        assertThat(response.duplicate()).isFalse();
        verify(scrapRepository, never()).findByUrl(any());
    }

    @Test
    void deletesScrap() {
        Scrap scrap = new Scrap("https://example.com", "제목", "본문", "본문",
            SourceType.ARTICLE, FallbackLevel.DIRECT_EXTRACTION, null, new float[]{0.1f});
        ReflectionTestUtils.setField(scrap, "id", 1L);
        when(scrapRepository.findById(1L)).thenReturn(Optional.of(scrap));

        scrapService.delete(1L);

        verify(scrapRepository).delete(scrap);
    }
}
