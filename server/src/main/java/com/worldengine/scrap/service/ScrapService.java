package com.worldengine.scrap.service;

import com.worldengine.extraction.model.ExtractionResult;
import com.worldengine.extraction.model.ExtractionStatus;
import com.worldengine.extraction.model.FailureReason;
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
import jakarta.persistence.EntityNotFoundException;
import java.util.List;
import java.util.Optional;
import org.springframework.stereotype.Service;

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

    public ScrapService(
        ContentExtractionService contentExtractionService,
        ScrapContentPreprocessor scrapContentPreprocessor,
        ContentSummaryClient contentSummaryClient,
        OpenAiEmbeddingClient openAiEmbeddingClient,
        ScrapRepository scrapRepository,
        RecommendationService recommendationService,
        IslandRepository islandRepository) {
        this.contentExtractionService = contentExtractionService;
        this.scrapContentPreprocessor = scrapContentPreprocessor;
        this.contentSummaryClient = contentSummaryClient;
        this.openAiEmbeddingClient = openAiEmbeddingClient;
        this.scrapRepository = scrapRepository;
        this.recommendationService = recommendationService;
        this.islandRepository = islandRepository;
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
        String summary = summarize(truncatedContent, extractionResult.fullPageText());
        boolean isBoilerplateOnly = truncatedContent != null && summary == null;

        float[] embedding = summary != null
            ? openAiEmbeddingClient.embed(summary)
            : null;

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

        List<IslandRecommendation> recommendations = embedding != null
            ? recommendationService.recommend(summary, embedding, RECALL_SIZE)
            : List.of();

        if (!recommendations.isEmpty()) {
            scrap.recordRecommendedIsland(recommendations.get(0).islandId());
        }

        Scrap saved = scrapRepository.save(scrap);

        ExtractionStatus status = isBoilerplateOnly ? ExtractionStatus.FAILED : extractionResult.status();

        return new ScrapCreateResponse(saved.getId(), saved.getTitle(),
            status, saved.getFailureReason(), recommendations,
            false, null, null);
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
    private String summarize(String truncatedContent, String fullPageText) {
        if (truncatedContent == null) {
            return null;
        }
        String result = contentSummaryClient.summarize(truncatedContent);
        if (!ContentSummaryClient.NO_CONTENT.equals(result)) {
            return result;
        }

        if (fullPageText == null) {
            return null;
        }

        String truncatedFullPage = scrapContentPreprocessor.truncateFullPage(fullPageText);
        String fallbackResult = contentSummaryClient.summarizeFullPage(truncatedFullPage);
        return ContentSummaryClient.NO_CONTENT.equals(fallbackResult) ? null : fallbackResult;
    }

    private ScrapCreateResponse duplicateResponse(Scrap existing) {
        String islandName = null;
        if (existing.getIslandId() != null) {
            islandName = islandRepository.findById(existing.getIslandId())
                .map(Island::getName)
                .orElse(null);
        }
        return new ScrapCreateResponse(existing.getId(), existing.getTitle(), null, null, List.of(),
            true, existing.getIslandId(), islandName);
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
            scrapRepository.save(scrap);
        }

        return recommendations;
    }

    public void delete(Long scrapId) {
        Scrap scrap = scrapRepository.findById(scrapId)
            .orElseThrow(() -> new EntityNotFoundException("존재하지 않는 스크랩: " + scrapId));
        scrapRepository.delete(scrap);
    }
}
