package com.worldengine.recommendation.service;

import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.recommendation.client.LlmPairwiseJudgeClient;
import com.worldengine.recommendation.vector.SimilarityResult;
import java.util.Comparator;
import java.util.List;
import org.springframework.stereotype.Service;

@Service
public class RecommendationService {

    private final IslandRecallService islandRecallService;
    private final IslandRepository islandRepository;
    private final LlmPairwiseJudgeClient llmPairwiseJudgeClient;

    public RecommendationService(
        IslandRecallService islandRecallService,
        IslandRepository islandRepository,
        LlmPairwiseJudgeClient llmPairwiseJudgeClient) {
        this.islandRecallService = islandRecallService;
        this.islandRepository = islandRepository;
        this.llmPairwiseJudgeClient = llmPairwiseJudgeClient;
    }

    public List<IslandRecommendation> recommend(String scrapSummary, float[] scrapEmbedding, int recallSize) {
        List<SimilarityResult> recalled = islandRecallService.recall(scrapEmbedding, recallSize);

        return recalled.stream()
            .map(result -> {
                Island island = islandRepository.findById(Long.valueOf(result.id())).orElseThrow();
                double llmScore = llmPairwiseJudgeClient.score(scrapSummary, island.getName());
                return new IslandRecommendation(island.getId(), island.getName(), llmScore);
            })
            .sorted(Comparator.comparingDouble(IslandRecommendation::llmScore).reversed()).toList();
    }
}
