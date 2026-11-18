package com.worldengine.island.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.scrap.repository.IslandMemberVector;
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
class IslandEmbeddingServiceTest {

    @Mock
    private IslandRepository islandRepository;

    @Mock
    private ScrapRepository scrapRepository;

    @InjectMocks
    private IslandEmbeddingService islandEmbeddingService;

    @Test
    void refreshesToMeanOfMemberEmbeddingsIgnoringScrapsWithoutEmbedding() {
        Island island = island(1L, new float[]{9f, 9f});
        when(islandRepository.findById(1L)).thenReturn(Optional.of(island));
        when(scrapRepository.findMemberVectorsByIslandId(1L)).thenReturn(List.of(
            member(new float[]{1f, 2f}),
            member(new float[]{3f, 4f})));

        islandEmbeddingService.refresh(1L);

        assertThat(island.getEmbedding()).containsExactly(2f, 3f);
        verify(islandRepository).save(island);
    }

    @Test
    void keepsExistingEmbeddingWhenNoMemberHasEmbedding() {
        Island island = island(1L, new float[]{9f, 9f});
        when(islandRepository.findById(1L)).thenReturn(Optional.of(island));
        when(scrapRepository.findMemberVectorsByIslandId(1L)).thenReturn(List.of());

        islandEmbeddingService.refresh(1L);

        assertThat(island.getEmbedding()).containsExactly(9f, 9f);
        verify(islandRepository, never()).save(any());
    }

    @Test
    void refreshAllRecomputesEveryIsland() {
        Island first = island(1L, new float[]{0f, 0f});
        Island second = island(2L, new float[]{0f, 0f});
        when(islandRepository.findAll()).thenReturn(List.of(first, second));
        when(islandRepository.findById(1L)).thenReturn(Optional.of(first));
        when(islandRepository.findById(2L)).thenReturn(Optional.of(second));
        when(scrapRepository.findMemberVectorsByIslandId(1L)).thenReturn(List.of(member(new float[]{1f, 1f})));
        when(scrapRepository.findMemberVectorsByIslandId(2L)).thenReturn(List.of(member(new float[]{2f, 2f})));

        int refreshed = islandEmbeddingService.refreshAll();

        assertThat(refreshed).isEqualTo(2);
        assertThat(first.getEmbedding()).containsExactly(1f, 1f);
        assertThat(second.getEmbedding()).containsExactly(2f, 2f);
    }

    private Island island(Long id, float[] embedding) {
        Island island = new Island("섬", embedding);
        ReflectionTestUtils.setField(island, "id", id);
        return island;
    }

    private IslandMemberVector member(float[] embedding) {
        return new IslandMemberVector(1L, "요약", embedding);
    }
}