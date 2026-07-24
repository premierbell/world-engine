package com.worldengine.scrap.service;

import com.worldengine.extraction.model.ExtractionResult;
import com.worldengine.extraction.service.ContentExtractionService;
import com.worldengine.recommendation.client.OpenAiEmbeddingClient;
import com.worldengine.recommendation.service.IslandRecommendation;
import com.worldengine.recommendation.service.RecommendationService;
import com.worldengine.scrap.dto.ScrapCreateResponse;
import com.worldengine.scrap.entity.Scrap;
import com.worldengine.scrap.repository.ScrapRepository;
import java.util.List;
import org.springframework.stereotype.Service;

@Service
public class ScrapService {

    private static final int RECALL_SIZE = 3;

    private final ContentExtractionService contentExtractionService;
    private final ScrapContentPreprocessor scrapContentPreprocessor;
    private final OpenAiEmbeddingClient openAiEmbeddingClient;
    private final ScrapRepository scrapRepository;
    private final RecommendationService recommendationService;

    public ScrapService(
        ContentExtractionService contentExtractionService,
        ScrapContentPreprocessor scrapContentPreprocessor,
        OpenAiEmbeddingClient openAiEmbeddingClient,
        ScrapRepository scrapRepository,
        RecommendationService recommendationService) {
        this.contentExtractionService = contentExtractionService;
        this.scrapContentPreprocessor = scrapContentPreprocessor;
        this.openAiEmbeddingClient = openAiEmbeddingClient;
        this.scrapRepository = scrapRepository;
        this.recommendationService = recommendationService;
    }

    public ScrapCreateResponse createScrap(String url, String userContext) {
        ExtractionResult extractionResult = contentExtractionService.extract(url);
        String truncatedContent = scrapContentPreprocessor.truncate(extractionResult.content());

        float[] embedding = truncatedContent != null
            ? openAiEmbeddingClient.embed(truncatedContent)
            : null;

        Scrap scrap = new Scrap(
            url,
            extractionResult.title(),
            extractionResult.content(),
            truncatedContent,
            extractionResult.sourceType(),
            extractionResult.fallbackLevel(),
            userContext,
            embedding
        );

        List<IslandRecommendation> recommendations = embedding != null
            ? recommendationService.recommend(truncatedContent, embedding, RECALL_SIZE)
            : List.of();

        if (!recommendations.isEmpty()) {
            scrap.recordRecommendedIsland(recommendations.get(0).islandId());
        }

        Scrap saved = scrapRepository.save(scrap);

        return new ScrapCreateResponse(saved.getId(), saved.getTitle(), extractionResult.status(), recommendations);
    }

}
