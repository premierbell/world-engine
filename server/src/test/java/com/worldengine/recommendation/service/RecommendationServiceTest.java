package com.worldengine.recommendation.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.recommendation.client.LlmPairwiseJudgeClient;
import com.worldengine.recommendation.vector.SimilarityResult;
import com.worldengine.scrap.repository.ScrapRepository;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class RecommendationServiceTest {

    @Mock
    private IslandRecallService islandRecallService;

    @Mock
    private IslandRepository islandRepository;

    @Mock
    private LlmPairwiseJudgeClient llmPairwiseJudgeClient;

    @Mock
    private ScrapRepository scrapRepository;

    @InjectMocks
    private RecommendationService recommendationService;

    @Test
    void reordersRecalledCandidatesByLlmScore() {
        Island diet = new Island("다이어트", new float[]{0.1f, 0.2f});
        Island backend = new Island("백엔드", new float[]{0.3f, 0.4f});
        ReflectionTestUtils.setField(diet, "id", 1L);
        ReflectionTestUtils.setField(backend, "id", 2L);

        float[] scrapEmbedding = {0.1f, 0.2f};
        when(scrapRepository.findMemberVectorsByIslandId(1L)).thenReturn(List.of());
        when(scrapRepository.findMemberVectorsByIslandId(2L)).thenReturn(List.of());
        when(islandRecallService.recall(scrapEmbedding, 2)).thenReturn(List.of(
            new SimilarityResult("1", 0.9),
            new SimilarityResult("2", 0.8)
        ));
        when(islandRepository.findById(1L)).thenReturn(Optional.of(diet));
        when(islandRepository.findById(2L)).thenReturn(Optional.of(backend));
        when(llmPairwiseJudgeClient.score("다이어트 식단 기록", "다이어트")).thenReturn(0.4);
        when(llmPairwiseJudgeClient.score("다이어트 식단 기록", "백엔드")).thenReturn(0.9);

        List<IslandRecommendation> result =
            recommendationService.recommend("다이어트 식단 기록", scrapEmbedding, 2);

        assertThat(result).hasSize(2);
        assertThat(result.get(0).islandName()).isEqualTo("백엔드");
        assertThat(result.get(1).islandName()).isEqualTo("다이어트");
    }

    @Test
    void callsLlmJudgeConcurrentlyForAllCandidates() {
        List<Island> islands = threeIslands();
        float[] scrapEmbedding = {0.1f, 0.2f};
        when(islandRecallService.recall(scrapEmbedding, 3)).thenReturn(List.of(
            new SimilarityResult("1", 0.9), new SimilarityResult("2", 0.8), new SimilarityResult("3", 0.7)));

        // 3개 호출이 동시에 진행 중이어야만 latch가 풀린다 - 순차 호출이면 첫 호출이 2초 기다리다 0.0을 반환
        CountDownLatch allInFlight = new CountDownLatch(3);
        when(llmPairwiseJudgeClient.score(eq("요약"), anyString())).thenAnswer(invocation -> {
            allInFlight.countDown();
            return allInFlight.await(2, TimeUnit.SECONDS) ? 0.5 : 0.0;
        });

        List<IslandRecommendation> result = recommendationService.recommend("요약", scrapEmbedding, 3);

        assertThat(result).extracting(IslandRecommendation::llmScore).containsOnly(0.5);
    }

    @Test
    void keepsCosineOrderWhenLlmScoresTie() {
        threeIslands();
        float[] scrapEmbedding = {0.1f, 0.2f};
        when(islandRecallService.recall(scrapEmbedding, 3)).thenReturn(List.of(
            new SimilarityResult("2", 0.9), new SimilarityResult("1", 0.8), new SimilarityResult("3", 0.7)));
        when(llmPairwiseJudgeClient.score(eq("요약"), anyString())).thenReturn(0.5);

        List<IslandRecommendation> result = recommendationService.recommend("요약", scrapEmbedding, 3);

        assertThat(result).extracting(IslandRecommendation::islandId).containsExactly(2L, 1L, 3L);
    }

    @Test
    void returnsEmptyWithoutCallingLlmWhenNothingRecalled() {
        float[] scrapEmbedding = {0.1f, 0.2f};
        when(islandRecallService.recall(scrapEmbedding, 3)).thenReturn(List.of());

        List<IslandRecommendation> result = recommendationService.recommend("요약", scrapEmbedding, 3);

        assertThat(result).isEmpty();
        verifyNoInteractions(llmPairwiseJudgeClient);
    }

    private List<Island> threeIslands() {
        List<Island> islands = List.of(
            new Island("여행", new float[]{0.1f, 0.2f}),
            new Island("백엔드", new float[]{0.3f, 0.4f}),
            new Island("AI", new float[]{0.5f, 0.6f}));
        for (int i = 0; i < islands.size(); i++) {
            long id = i + 1;
            ReflectionTestUtils.setField(islands.get(i), "id", id);
            when(islandRepository.findById(id)).thenReturn(Optional.of(islands.get(i)));
            when(scrapRepository.findMemberVectorsByIslandId(id)).thenReturn(List.of());
        }
        return islands;
    }
}
