package com.worldengine.scrap.service;

import com.worldengine.extraction.model.ExtractionResult;
import com.worldengine.extraction.model.ExtractionStatus;
import com.worldengine.extraction.model.FailureReason;
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
import com.worldengine.scrap.model.PendingAiStep;
import com.worldengine.scrap.repository.ScrapRepository;
import jakarta.persistence.EntityNotFoundException;
import java.util.List;
import java.util.Optional;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;

@Slf4j
@Service
public class ScrapService {

    private static final int RECALL_SIZE = 3;

    private final ContentExtractionService contentExtractionService;
    private final ScrapContentPreprocessor scrapContentPreprocessor;
    private final ContentSummaryClient contentSummaryClient;
    private final OpenAiEmbeddingClient openAiEmbeddingClient;
    private final ScrapRepository scrapRepository;
    private final RecommendationService recommendationService;
    private final IslandRepository islandRepository;
    private final IslandEmbeddingService islandEmbeddingService;

    public ScrapService(
        ContentExtractionService contentExtractionService,
        ScrapContentPreprocessor scrapContentPreprocessor,
        ContentSummaryClient contentSummaryClient,
        OpenAiEmbeddingClient openAiEmbeddingClient,
        ScrapRepository scrapRepository,
        RecommendationService recommendationService,
        IslandRepository islandRepository,
        IslandEmbeddingService islandEmbeddingService) {
        this.contentExtractionService = contentExtractionService;
        this.scrapContentPreprocessor = scrapContentPreprocessor;
        this.contentSummaryClient = contentSummaryClient;
        this.openAiEmbeddingClient = openAiEmbeddingClient;
        this.scrapRepository = scrapRepository;
        this.recommendationService = recommendationService;
        this.islandRepository = islandRepository;
        this.islandEmbeddingService = islandEmbeddingService;
    }

    public ScrapCreateResponse createScrap(String url, String userContext) {
        return createScrap(url, userContext, false);
    }

    public ScrapCreateResponse createScrap(String url, String userContext, boolean force) {
        if (!force) {
            Optional<Scrap> existing = scrapRepository.findByUrl(url);
            if (existing.isPresent()) {
                return duplicateResponse(existing.get());
            }
        }

        ExtractionResult extractionResult = contentExtractionService.extract(url);
        String truncatedContent = scrapContentPreprocessor.truncate(extractionResult.content());

        // OpenAI 장애로 AI 단계가 실패해도 추출한 본문은 버리지 않는다 - 실패한 단계만 표시하고 저장한다
        // (experiments/v0_validation.md 2026-11-18 장애 측정: 장애 7개 전부 본문 유실).
        // RestClientException(HTTP 오류·타임아웃)만 잡는다 - 그 밖의 예외는 코드 버그라 숨기지 않는다.
        PendingAiStep pendingAiStep = null;
        String summary = null;
        float[] embedding = null;
        try {
            summary = summarize(url, truncatedContent, extractionResult.fullPageText());
            embedding = summary != null ? openAiEmbeddingClient.embed(summary) : null;
        } catch (RestClientException e) {
            log.warn("AI 요약/임베딩 실패 - 본문만 저장하고 요약 대기로 표시 - url={}", url, e);
            pendingAiStep = PendingAiStep.SUMMARY;
        }
        boolean isBoilerplateOnly = pendingAiStep == null && truncatedContent != null && summary == null;

        List<IslandRecommendation> recommendations = List.of();
        if (embedding != null) {
            try {
                recommendations = recommendationService.recommend(summary, embedding, RECALL_SIZE);
            } catch (RestClientException e) {
                log.warn("추천 판정 실패 - 요약·임베딩까지 저장하고 추천 대기로 표시 - url={}", url, e);
                pendingAiStep = PendingAiStep.RECOMMENDATION;
            }
        }

        Scrap scrap = new Scrap(
            url,
            extractionResult.title(),
            extractionResult.content(),
            summary,
            extractionResult.sourceType(),
            extractionResult.fallbackLevel(),
            userContext,
            embedding
        );
        scrap.recordFailureReason(isBoilerplateOnly ? FailureReason.BOILERPLATE_ONLY : extractionResult.failureReason());
        scrap.recordPendingAiStep(pendingAiStep);

        if (!recommendations.isEmpty()) {
            scrap.recordRecommendedIsland(recommendations.get(0).islandId());
        }

        Scrap saved = scrapRepository.save(scrap);

        ExtractionStatus status = isBoilerplateOnly ? ExtractionStatus.FAILED : extractionResult.status();

        return new ScrapCreateResponse(saved.getId(), saved.getTitle(),
            status, saved.getFailureReason(), recommendations,
            false, null, null, saved.getPendingAiStep());
    }

    /**
     * 원문이 저작권/약관/편집제한 안내 같은 사이트 운영 정책 문구뿐이면
     * ContentSummaryClient가 NO_CONTENT를 반환함 - 이 경우 summary를 null로
     * 처리(embedding/추천도 자동으로 스킵됨, extractionResult.content()가
     * null일 때와 같은 경로) - 별도 "오염 의심" 플래그 없이 summary가
     * 비어있다는 것 자체가 신호가 된다.
     *
     * 1차(readability4j가 고른 좁은 범위)에서 NO_CONTENT가 나오면,
     * fullPageText(페이지 전체 텍스트)가 있는 경우에 한해 2차 폴백을
     * 시도한다 - readability4j가 본문 선택을 잘못했을 뿐 실제로는 페이지에
     * 내용이 있는 경우(KT위즈샵 상품 페이지처럼 상품 정보가 표/목록 형태로
     * 흩어져 있어 readability4j가 반품정책만 고른 사례)를 구제하기 위함.
     * 정상 페이지는 1차에서 바로 끝나므로 AI 호출이 추가되지 않는다.
     */
    private String summarize(String url, String truncatedContent, String fullPageText) {
        if (truncatedContent == null) {
            return null;
        }
        String result = contentSummaryClient.summarize(truncatedContent);
        if (!ContentSummaryClient.NO_CONTENT.equals(result)) {
            return result;
        }

        log.info("1차 요약 NO_CONTENT - 전체 페이지 폴백 시도 - url={}", url);

        if (fullPageText == null) {
            return null;
        }

        String truncatedFullPage = scrapContentPreprocessor.truncateFullPage(fullPageText);
        String fallbackResult = contentSummaryClient.summarizeFullPage(truncatedFullPage);

        if (ContentSummaryClient.NO_CONTENT.equals(fallbackResult)) {
            log.info("전체 페이지 폴백도 NO_CONTENT - BOILERPLATE_ONLY로 확정 - url={}", url);
            return null;
        }

        log.info("전체 페이지 폴백 성공 - url={}", url);

        return fallbackResult;
    }

    private ScrapCreateResponse duplicateResponse(Scrap existing) {
        String islandName = null;
        if (existing.getIslandId() != null) {
            islandName = islandRepository.findById(existing.getIslandId())
                .map(Island::getName)
                .orElse(null);
        }
        return new ScrapCreateResponse(existing.getId(), existing.getTitle(), null, null, List.of(),
            true, existing.getIslandId(), islandName, existing.getPendingAiStep());
    }

    public List<IslandRecommendation> refreshRecommendations(Long scrapId) {
        Scrap scrap = scrapRepository.findById(scrapId)
            .orElseThrow(() -> new EntityNotFoundException("존재하지 않는 스크랩: " + scrapId));

        if (scrap.getIslandId() != null) {
            throw new IllegalArgumentException("이미 확정된 스크랩은 추천을 다시 계산할 수 없음: " + scrapId);
        }

        if (scrap.getEmbedding() == null) {
            return List.of();
        }

        List<IslandRecommendation> recommendations =
            recommendationService.recommend(scrap.getSummary(), scrap.getEmbedding(), RECALL_SIZE);

        if (!recommendations.isEmpty()) {
            scrap.recordRecommendedIsland(recommendations.get(0).islandId());
        }
        scrap.recordPendingAiStep(null);
        scrapRepository.save(scrap);

        return recommendations;
    }

    /**
     * 이미 저장된 content(원문)를 그대로 재요약한다 - URL을 다시 안 가져오므로
     * 생성 시각/섬·Topic 배정/wasCorrected 이력은 전혀 건드리지 않는다.
     * fullPageText가 없으므로 1차 요약만 시도하고, 그마저 NO_CONTENT면
     * BOILERPLATE_ONLY로 기록한다(2차 폴백은 URL 재추출이 필요해서 여기선 불가).
     */
    public ScrapCreateResponse resummarize(Long scrapId) {
        Scrap scrap = scrapRepository.findById(scrapId)
            .orElseThrow(() -> new EntityNotFoundException("존재하지 않는 스크랩: " + scrapId));

        String truncatedContent = scrapContentPreprocessor.truncate(scrap.getContent());
        String summary = summarize(scrap.getUrl(), truncatedContent, null);
        boolean isBoilerplateOnly = truncatedContent != null && summary == null;

        float[] embedding = summary != null ? openAiEmbeddingClient.embed(summary) : null;

        scrap.updateSummaryAndEmbedding(summary, embedding);
        scrap.recordFailureReason(isBoilerplateOnly ? FailureReason.BOILERPLATE_ONLY : FailureReason.NONE);

        // 요약이 복구됐다. 미확정 스크랩은 새 임베딩으로 추천을 다시 받아야 하므로 추천 대기로 넘긴다.
        boolean needsRecommendation = scrap.getIslandId() == null && embedding != null;
        scrap.recordPendingAiStep(needsRecommendation ? PendingAiStep.RECOMMENDATION : null);

        Scrap saved = scrapRepository.save(scrap);

        // 임베딩이 바뀌었으니 소속 섬의 대표 벡터도 다시 계산 - 이게 빠져 있어서
        // AI 요약 백필(PR #139) 이후 섬 벡터가 낡은 채로 남아 있었다
        if (saved.getIslandId() != null) {
            islandEmbeddingService.refresh(saved.getIslandId());
        }

        ExtractionStatus status = isBoilerplateOnly ? ExtractionStatus.FAILED : ExtractionStatus.SUCCESS;

        return new ScrapCreateResponse(saved.getId(), saved.getTitle(), status, saved.getFailureReason(),
            List.of(), false, null, null, saved.getPendingAiStep());
    }

    public void delete(Long scrapId) {
        Scrap scrap = scrapRepository.findById(scrapId)
            .orElseThrow(() -> new EntityNotFoundException("존재하지 않는 스크랩: " + scrapId));
        Long islandId = scrap.getIslandId();

        scrapRepository.delete(scrap);

        if (islandId != null) {
            islandEmbeddingService.refresh(islandId);
        }
    }
}
