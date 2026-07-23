package com.worldengine.recommendation.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.recommendation.vector.SimilarityResult;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class IslandRecallServiceTest {

    @Mock
    private IslandRepository islandRepository;

    @InjectMocks
    private IslandRecallService islandRecallService;

    @Test
    void recallsClosestIslandsByCosineSimilarity() {
        Island close = new Island("close", new float[]{0.9f, 0.1f});
        Island far = new Island("far", new float[]{-1f, 0f});
        ReflectionTestUtils.setField(close, "id", 1L);
        ReflectionTestUtils.setField(far, "id", 2L);
        when(islandRepository.findAll()).thenReturn(List.of(close, far));

        List<SimilarityResult> top1 = islandRecallService.recall(new float[]{1f, 0f}, 1);

        assertThat(top1).hasSize(1);
        assertThat(top1.get(0).id()).isEqualTo("1");
    }
}
