package com.worldengine.recommendation.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.recommendation.client.LlmPairwiseJudgeClient;
import com.worldengine.recommendation.vector.SimilarityResult;
import com.worldengine.scrap.repository.ScrapRepository;
import java.util.List;
import java.util.Optional;
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
        when(scrapRepository.findByIslandId(1L)).thenReturn(List.of());
        when(scrapRepository.findByIslandId(2L)).thenReturn(List.of());
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

}
