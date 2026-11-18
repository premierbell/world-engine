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
import com.worldengine.island.service.IslandEmbeddingService;
import com.worldengine.recommendation.client.ContentSummaryClient;
import com.worldengine.recommendation.client.OpenAiEmbeddingClient;
import com.worldengine.recommendation.service.IslandRecommendation;
import com.worldengine.recommendation.service.RecommendationService;
import com.worldengine.scrap.dto.ScrapCreateResponse;
import com.worldengine.scrap.entity.Scrap;
import com.worldengine.scrap.repository.ScrapRepository;
import com.worldengine.scrap.model.PendingAiStep;
import org.mockito.ArgumentCaptor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.ResourceAccessException;
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

    @Mock
    private IslandEmbeddingService islandEmbeddingService;

    @Spy
    private ScrapContentPreprocessor scrapContentPreprocessor = new ScrapContentPreprocessor(2000, 6000);

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
        verify(islandEmbeddingService, never()).refresh(any());
    }

    @Test
    void refreshesIslandEmbeddingAfterDeletingConfirmedScrap() {
        Scrap scrap = new Scrap("https://example.com", "제목", "본문", "본문",
            SourceType.ARTICLE, FallbackLevel.DIRECT_EXTRACTION, null, new float[]{0.1f});
        ReflectionTestUtils.setField(scrap, "id", 1L);
        scrap.confirmIsland(7L);
        when(scrapRepository.findById(1L)).thenReturn(Optional.of(scrap));

        scrapService.delete(1L);

        verify(scrapRepository).delete(scrap);
        verify(islandEmbeddingService).refresh(7L);
    }

    @Test
    void resummarizesScrapUsingStoredContentOnly() {
        Scrap scrap = new Scrap("https://example.com", "제목", "저장된 원문", "예전 요약",
            SourceType.ARTICLE, FallbackLevel.DIRECT_EXTRACTION, null, new float[]{0.9f});
        ReflectionTestUtils.setField(scrap, "id", 30L);
        scrap.confirmIsland(7L);
        when(scrapRepository.findById(30L)).thenReturn(Optional.of(scrap));
        when(contentSummaryClient.summarize("저장된 원문")).thenReturn("새 요약");
        float[] newEmbedding = {0.5f, 0.6f};
        when(openAiEmbeddingClient.embed("새 요약")).thenReturn(newEmbedding);
        when(scrapRepository.save(scrap)).thenReturn(scrap);

        ScrapCreateResponse response = scrapService.resummarize(30L);

        assertThat(response.status()).isEqualTo(ExtractionStatus.SUCCESS);
        assertThat(scrap.getSummary()).isEqualTo("새 요약");
        assertThat(scrap.getEmbedding()).isEqualTo(newEmbedding);
        assertThat(scrap.getIslandId()).isEqualTo(7L);
        verify(contentExtractionService, never()).extract(any());
        verify(islandEmbeddingService).refresh(7L);
    }

    @Test
    void marksBoilerplateOnlyWhenResummarizeFindsNoContent() {
        Scrap scrap = new Scrap("https://example.com/old", "제목", "저작권 안내만 있음", "예전 요약(사실 그냥 자른 것)",
            SourceType.ARTICLE, FallbackLevel.DIRECT_EXTRACTION, null, new float[]{0.9f});
        ReflectionTestUtils.setField(scrap, "id", 31L);
        when(scrapRepository.findById(31L)).thenReturn(Optional.of(scrap));
        when(contentSummaryClient.summarize("저작권 안내만 있음")).thenReturn("NO_CONTENT");
        when(scrapRepository.save(scrap)).thenReturn(scrap);

        ScrapCreateResponse response = scrapService.resummarize(31L);

        assertThat(response.status()).isEqualTo(ExtractionStatus.FAILED);
        assertThat(response.failureReason()).isEqualTo(FailureReason.BOILERPLATE_ONLY);
        assertThat(scrap.getSummary()).isNull();
        verify(openAiEmbeddingClient, never()).embed(any());
        verify(islandEmbeddingService, never()).refresh(any());
    }

    @Test
    void fallsBackToFullPageWhenNarrowContentIsBoilerplate() {
        ExtractionResult extractionResult = new ExtractionResult(
            ExtractionStatus.SUCCESS, "제목", "반품 정책 문구", null,
            SourceType.ARTICLE, FallbackLevel.DIRECT_EXTRACTION, FailureReason.NONE,
            "메뉴 반품 정책 문구 상품명 케이티위즈 유니폼 109000원"
        );
        when(contentExtractionService.extract("https://example.com/product")).thenReturn(extractionResult);
        when(contentSummaryClient.summarize("반품 정책 문구")).thenReturn("NO_CONTENT");
        when(contentSummaryClient.summarizeFullPage("메뉴 반품 정책 문구 상품명 케이티위즈 유니폼 109000원"))
            .thenReturn("케이티위즈 유니폼, 109000원");

        float[] embedding = {0.1f, 0.2f};
        when(openAiEmbeddingClient.embed("케이티위즈 유니폼, 109000원")).thenReturn(embedding);

        Scrap saved = new Scrap("https://example.com/product", "제목", "반품 정책 문구", "케이티위즈 유니폼, 109000원",
            SourceType.ARTICLE, FallbackLevel.DIRECT_EXTRACTION, null, embedding);
        ReflectionTestUtils.setField(saved, "id", 20L);
        when(scrapRepository.save(any())).thenReturn(saved);
        when(recommendationService.recommend(any(), any(), anyInt())).thenReturn(List.of());

        ScrapCreateResponse response = scrapService.createScrap("https://example.com/product", null);

        assertThat(response.status()).isEqualTo(ExtractionStatus.SUCCESS);
        verify(contentSummaryClient).summarizeFullPage("메뉴 반품 정책 문구 상품명 케이티위즈 유니폼 109000원");
    }

    // ===== OpenAI 장애 시 본문 보존 (experiments/v0_validation.md 2026-11-18 장애 측정, 개선 B) =====

    private static final String FAULT_URL = "https://example.com/fault";

    @Test
    void 요약이_장애로_실패하면_본문만_저장하고_요약_대기로_표시한다() {
        when(contentExtractionService.extract(FAULT_URL))
            .thenReturn(ExtractionResult.success("제목", "본문 내용", SourceType.ARTICLE));
        when(contentSummaryClient.summarize("본문 내용")).thenThrow(new ResourceAccessException("request timed out"));
        when(scrapRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        ScrapCreateResponse response = scrapService.createScrap(FAULT_URL, null);

        Scrap saved = captureSaved();
        assertThat(saved.getContent()).isEqualTo("본문 내용");
        assertThat(saved.getSummary()).isNull();
        assertThat(saved.getPendingAiStep()).isEqualTo(PendingAiStep.SUMMARY);
        // 장애로 요약이 비었을 뿐이라 "정책 문구뿐"으로 잘못 기록하면 안 된다
        assertThat(saved.getFailureReason()).isNotEqualTo(FailureReason.BOILERPLATE_ONLY);
        assertThat(response.status()).isEqualTo(ExtractionStatus.SUCCESS);
        assertThat(response.pendingAiStep()).isEqualTo(PendingAiStep.SUMMARY);
        verify(openAiEmbeddingClient, never()).embed(any());
        verify(recommendationService, never()).recommend(any(), any(), anyInt());
    }

    @Test
    void 임베딩이_장애로_실패하면_요약까지_저장하고_요약_대기로_표시한다() {
        when(contentExtractionService.extract(FAULT_URL))
            .thenReturn(ExtractionResult.success("제목", "본문 내용", SourceType.ARTICLE));
        when(contentSummaryClient.summarize("본문 내용")).thenReturn("요약");
        when(openAiEmbeddingClient.embed("요약")).thenThrow(serverError());
        when(scrapRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        ScrapCreateResponse response = scrapService.createScrap(FAULT_URL, null);

        Scrap saved = captureSaved();
        assertThat(saved.getSummary()).isEqualTo("요약");
        assertThat(saved.getEmbedding()).isNull();
        assertThat(saved.getPendingAiStep()).isEqualTo(PendingAiStep.SUMMARY);
        assertThat(response.pendingAiStep()).isEqualTo(PendingAiStep.SUMMARY);
        verify(recommendationService, never()).recommend(any(), any(), anyInt());
    }

    @Test
    void 추천_판정이_장애로_실패하면_요약과_임베딩을_보존하고_추천_대기로_표시한다() {
        float[] embedding = {0.1f, 0.2f};
        when(contentExtractionService.extract(FAULT_URL))
            .thenReturn(ExtractionResult.success("제목", "본문 내용", SourceType.ARTICLE));
        when(contentSummaryClient.summarize("본문 내용")).thenReturn("요약");
        when(openAiEmbeddingClient.embed("요약")).thenReturn(embedding);
        when(recommendationService.recommend("요약", embedding, 3)).thenThrow(serverError());
        when(scrapRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        ScrapCreateResponse response = scrapService.createScrap(FAULT_URL, null);

        Scrap saved = captureSaved();
        assertThat(saved.getSummary()).isEqualTo("요약");
        assertThat(saved.getEmbedding()).isEqualTo(embedding);
        assertThat(saved.getRecommendedIslandId()).isNull();
        assertThat(saved.getPendingAiStep()).isEqualTo(PendingAiStep.RECOMMENDATION);
        assertThat(response.recommendations()).isEmpty();
        assertThat(response.pendingAiStep()).isEqualTo(PendingAiStep.RECOMMENDATION);
    }

    @Test
    void OpenAI_장애가_아닌_예외는_숨기지_않고_저장도_하지_않는다() {
        when(contentExtractionService.extract(FAULT_URL))
            .thenReturn(ExtractionResult.success("제목", "본문 내용", SourceType.ARTICLE));
        when(contentSummaryClient.summarize("본문 내용")).thenThrow(new IllegalStateException("코드 버그"));

        assertThatThrownBy(() -> scrapService.createScrap(FAULT_URL, null))
            .isInstanceOf(IllegalStateException.class);
        verify(scrapRepository, never()).save(any());
    }

    @Test
    void 추천을_다시_받으면_추천_대기가_해제된다() {
        float[] embedding = {0.1f, 0.2f};
        Scrap scrap = new Scrap(FAULT_URL, "제목", "본문 내용", "요약",
            SourceType.ARTICLE, FallbackLevel.DIRECT_EXTRACTION, null, embedding);
        scrap.recordPendingAiStep(PendingAiStep.RECOMMENDATION);
        when(scrapRepository.findById(1L)).thenReturn(Optional.of(scrap));
        when(recommendationService.recommend("요약", embedding, 3))
            .thenReturn(List.of(new IslandRecommendation(2L, "여행", 0.9)));

        scrapService.refreshRecommendations(1L);

        assertThat(scrap.getPendingAiStep()).isNull();
        assertThat(scrap.getRecommendedIslandId()).isEqualTo(2L);
        verify(scrapRepository).save(scrap);
    }

    @Test
    void 추천을_다시_받다가_또_실패하면_추천_대기가_그대로_남는다() {
        float[] embedding = {0.1f, 0.2f};
        Scrap scrap = new Scrap(FAULT_URL, "제목", "본문 내용", "요약",
            SourceType.ARTICLE, FallbackLevel.DIRECT_EXTRACTION, null, embedding);
        scrap.recordPendingAiStep(PendingAiStep.RECOMMENDATION);
        when(scrapRepository.findById(1L)).thenReturn(Optional.of(scrap));
        when(recommendationService.recommend("요약", embedding, 3)).thenThrow(serverError());

        assertThatThrownBy(() -> scrapService.refreshRecommendations(1L))
            .isInstanceOf(HttpServerErrorException.class);
        assertThat(scrap.getPendingAiStep()).isEqualTo(PendingAiStep.RECOMMENDATION);
        verify(scrapRepository, never()).save(any());
    }

    @Test
    void 미확정_스크랩의_요약이_복구되면_추천_대기로_넘어간다() {
        float[] embedding = {0.1f, 0.2f};
        Scrap scrap = new Scrap(FAULT_URL, "제목", "본문 내용", null,
            SourceType.ARTICLE, FallbackLevel.DIRECT_EXTRACTION, null, null);
        scrap.recordPendingAiStep(PendingAiStep.SUMMARY);
        when(scrapRepository.findById(1L)).thenReturn(Optional.of(scrap));
        when(contentSummaryClient.summarize("본문 내용")).thenReturn("요약");
        when(openAiEmbeddingClient.embed("요약")).thenReturn(embedding);
        when(scrapRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        ScrapCreateResponse response = scrapService.resummarize(1L);

        assertThat(scrap.getPendingAiStep()).isEqualTo(PendingAiStep.RECOMMENDATION);
        assertThat(response.pendingAiStep()).isEqualTo(PendingAiStep.RECOMMENDATION);
    }

    @Test
    void 확정된_스크랩의_요약이_복구되면_대기가_해제된다() {
        float[] embedding = {0.1f, 0.2f};
        Scrap scrap = new Scrap(FAULT_URL, "제목", "본문 내용", null,
            SourceType.ARTICLE, FallbackLevel.DIRECT_EXTRACTION, null, null);
        scrap.confirmIsland(5L);
        scrap.recordPendingAiStep(PendingAiStep.SUMMARY);
        when(scrapRepository.findById(1L)).thenReturn(Optional.of(scrap));
        when(contentSummaryClient.summarize("본문 내용")).thenReturn("요약");
        when(openAiEmbeddingClient.embed("요약")).thenReturn(embedding);
        when(scrapRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        scrapService.resummarize(1L);

        assertThat(scrap.getPendingAiStep()).isNull();
    }

    private Scrap captureSaved() {
        ArgumentCaptor<Scrap> captor = ArgumentCaptor.forClass(Scrap.class);
        verify(scrapRepository).save(captor.capture());
        return captor.getValue();
    }

    private static HttpServerErrorException serverError() {
        return HttpServerErrorException.create(HttpStatus.INTERNAL_SERVER_ERROR, "Internal Server Error",
            HttpHeaders.EMPTY, null, null);
    }
}
