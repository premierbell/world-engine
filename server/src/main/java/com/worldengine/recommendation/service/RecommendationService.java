package com.worldengine.recommendation.service;

import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.recommendation.client.LlmPairwiseJudgeClient;
import com.worldengine.recommendation.vector.CosineSimilarity;
import com.worldengine.recommendation.vector.SimilarityResult;
import com.worldengine.scrap.repository.IslandMemberVector;
import com.worldengine.scrap.repository.ScrapRepository;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
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

    /**
     * Cosine Top-K(Recall) 후보를 LLM Pairwise 점수로 재정렬한다(Precision).
     * LLM 호출은 후보마다 독립이라 병렬로 보낸다 - 순차 p50 1.90초 vs 병렬 0.73초,
     * 추천 단계가 스크랩 생성 시간의 약 40%였다(experiments/v0_validation.md, 2026-11-18).
     * DB 조회(섬, 대표 텍스트)는 호출 스레드에서 먼저 끝내고 LLM 호출만 병렬로 보낸다.
     */
    public List<IslandRecommendation> recommend(String scrapSummary, float[] scrapEmbedding, int recallSize) {
        List<SimilarityResult> recalled = islandRecallService.recall(scrapEmbedding, recallSize);
        if (recalled.isEmpty()) {
            return List.of();
        }

        List<Island> islands = recalled.stream()
            .map(result -> islandRepository.findById(Long.valueOf(result.id())).orElseThrow())
            .toList();
        List<String> comparisonTexts = islands.stream()
            .map(island -> representativeText(island, scrapEmbedding))
            .toList();

        List<Double> llmScores;
        try (ExecutorService executor = Executors.newFixedThreadPool(islands.size())) {
            List<CompletableFuture<Double>> futures = comparisonTexts.stream()
                .map(text -> CompletableFuture.supplyAsync(
                    () -> llmPairwiseJudgeClient.score(scrapSummary, text), executor))
                .toList();
            llmScores = futures.stream().map(this::joinUnwrapped).toList();
        }

        List<IslandRecommendation> recommendations = new ArrayList<>();
        for (int i = 0; i < islands.size(); i++) {
            Island island = islands.get(i);
            recommendations.add(new IslandRecommendation(island.getId(), island.getName(), llmScores.get(i)));
        }
        // 안정 정렬 - LLM 점수가 같으면 Cosine 순서를 유지(기존 동작과 동일)
        recommendations.sort(Comparator.comparingDouble(IslandRecommendation::llmScore).reversed());
        return recommendations;
    }

    /** join()이 감싸는 CompletionException을 풀어서 원래 예외를 그대로 던진다 - 기존 순차 호출과 같은 예외가 보이도록. */
    private double joinUnwrapped(CompletableFuture<Double> future) {
        try {
            return future.join();
        } catch (CompletionException e) {
            if (e.getCause() instanceof RuntimeException cause) {
                throw cause;
            }
            throw e;
        }
    }

    private String representativeText(Island island, float[] queryEmbedding) {
        return scrapRepository.findMemberVectorsByIslandId(island.getId()).stream()
            .filter(member -> member.summary() != null && !member.summary().isBlank())
            .max(Comparator.comparingDouble(member -> CosineSimilarity.similarity(queryEmbedding, member.embedding())))
            .map(IslandMemberVector::summary)
            .orElse(island.getName());
    }
}
