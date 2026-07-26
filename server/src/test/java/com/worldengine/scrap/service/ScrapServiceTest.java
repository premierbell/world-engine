package com.worldengine.scrap.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.worldengine.extraction.model.ExtractionResult;
import com.worldengine.extraction.model.FailureReason;
import com.worldengine.extraction.model.FallbackLevel;
import com.worldengine.extraction.model.SourceType;
import com.worldengine.extraction.service.ContentExtractionService;
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
    private OpenAiEmbeddingClient openAiEmbeddingClient;

    @Mock
    private ScrapRepository scrapRepository;

    @Mock
    private RecommendationService recommendationService;

    @Spy
    private ScrapContentPreprocessor scrapContentPreprocessor = new ScrapContentPreprocessor(2000);

    @InjectMocks
    private ScrapService scrapService;

    @Test
    void createsScrapAndReturnsRecommendationsWhenExtractionSucceeds() {
        ExtractionResult extractionResult = ExtractionResult.success("제목", "본문 내용", SourceType.ARTICLE);
        when(contentExtractionService.extract("https://example.com")).thenReturn(extractionResult);

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
        verify(openAiEmbeddingClient, never()).embed(any());
        verify(recommendationService, never()).recommend(any(), any(), anyInt());
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
}
