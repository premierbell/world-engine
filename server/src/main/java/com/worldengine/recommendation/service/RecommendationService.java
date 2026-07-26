package com.worldengine.recommendation.service;

import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.recommendation.client.LlmPairwiseJudgeClient;
import com.worldengine.recommendation.vector.CosineSimilarity;
import com.worldengine.recommendation.vector.SimilarityResult;
import com.worldengine.scrap.entity.Scrap;
import com.worldengine.scrap.repository.ScrapRepository;
import java.util.Comparator;
import java.util.List;
import org.springframework.stereotype.Service;

@Service
public class RecommendationService {

    private final IslandRecallService islandRecallService;
    private final IslandRepository islandRepository;
    private final ScrapRepository scrapRepository;
    private final LlmPairwiseJudgeClient llmPairwiseJudgeClient;

    public RecommendationService(
        IslandRecallService islandRecallService,
        IslandRepository islandRepository,
        ScrapRepository scrapRepository,
        LlmPairwiseJudgeClient llmPairwiseJudgeClient) {
        this.islandRecallService = islandRecallService;
        this.islandRepository = islandRepository;
        this.scrapRepository = scrapRepository;
        this.llmPairwiseJudgeClient = llmPairwiseJudgeClient;
    }

    public List<IslandRecommendation> recommend(String scrapSummary, float[] scrapEmbedding, int recallSize) {
        List<SimilarityResult> recalled = islandRecallService.recall(scrapEmbedding, recallSize);

        return recalled.stream()
            .map(result -> {
                Island island = islandRepository.findById(Long.valueOf(result.id())).orElseThrow();
                String comparisonText = representativeText(island, scrapEmbedding);
                double llmScore = llmPairwiseJudgeClient.score(scrapSummary, comparisonText);
                return new IslandRecommendation(island.getId(), island.getName(), llmScore);
            })
            .sorted(Comparator.comparingDouble(IslandRecommendation::llmScore).reversed()).toList();
    }

    private String representativeText(Island island, float[] queryEmbedding) {
        return scrapRepository.findByIslandId(island.getId()).stream()
            .filter(scrap -> scrap.getEmbedding() != null
                && scrap.getSummary() != null
                && !scrap.getSummary().isBlank())
            .max(Comparator.comparingDouble(scrap -> CosineSimilarity.similarity(queryEmbedding, scrap.getEmbedding())))
            .map(Scrap::getSummary)
            .orElse(island.getName());
    }
}
