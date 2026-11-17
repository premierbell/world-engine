package com.worldengine.island.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.scrap.entity.Scrap;
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
        when(scrapRepository.findByIslandId(1L)).thenReturn(List.of(
            scrap(new float[]{1f, 2f}),
            scrap(new float[]{3f, 4f}),
            scrap(null)));

        islandEmbeddingService.refresh(1L);

        assertThat(island.getEmbedding()).containsExactly(2f, 3f);
        verify(islandRepository).save(island);
    }

    @Test
    void keepsExistingEmbeddingWhenNoMemberHasEmbedding() {
        Island island = island(1L, new float[]{9f, 9f});
        when(islandRepository.findById(1L)).thenReturn(Optional.of(island));
        when(scrapRepository.findByIslandId(1L)).thenReturn(List.of(scrap(null)));

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
        when(scrapRepository.findByIslandId(1L)).thenReturn(List.of(scrap(new float[]{1f, 1f})));
        when(scrapRepository.findByIslandId(2L)).thenReturn(List.of(scrap(new float[]{2f, 2f})));

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

    private Scrap scrap(float[] embedding) {
        return new Scrap("https://example.com", "제목", "본문", "요약",
            null, null, null, embedding);
    }
}