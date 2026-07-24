package com.worldengine.scrap.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.scrap.dto.ScrapConfirmResponse;
import com.worldengine.scrap.entity.Scrap;
import com.worldengine.scrap.repository.ScrapRepository;
import jakarta.persistence.EntityNotFoundException;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class ScrapConfirmServiceTest {

    @Mock
    private ScrapRepository scrapRepository;

    @Mock
    private IslandRepository islandRepository;

    @InjectMocks
    private ScrapConfirmService scrapConfirmService;

    @Test
    void confirmsWithExistingIsland() {
        Scrap scrap = new Scrap("https://example.com", "제목", "본문", "본문",
            null, null, null, new float[]{0.1f, 0.2f});
        ReflectionTestUtils.setField(scrap, "id", 1L);
        Island island = new Island("다이어트", new float[]{0.3f, 0.4f});
        ReflectionTestUtils.setField(island, "id", 10L);

        when(scrapRepository.findById(1L)).thenReturn(Optional.of(scrap));
        when(islandRepository.findById(10L)).thenReturn(Optional.of(island));
        when(scrapRepository.save(any())).thenReturn(scrap);

        ScrapConfirmResponse response = scrapConfirmService.confirm(1L, 10L, null);

        assertThat(response.islandId()).isEqualTo(10L);
        assertThat(scrap.getIslandId()).isEqualTo(10L);
    }

    @Test
    void confirmsWithNewIslandUsingScrapEmbedding() {
        float[] embedding = {0.1f, 0.2f};
        Scrap scrap = new Scrap("https://example.com", "제목", "본문", "본문",
            null, null, null, embedding);
        ReflectionTestUtils.setField(scrap, "id", 1L);

        when(scrapRepository.findById(1L)).thenReturn(Optional.of(scrap));
        when(islandRepository.save(any())).thenAnswer(invocation -> {
            Island island = invocation.getArgument(0);
            ReflectionTestUtils.setField(island, "id", 20L);
            return island;
        });
        when(scrapRepository.save(any())).thenReturn(scrap);

        ScrapConfirmResponse response = scrapConfirmService.confirm(1L, null, "새로운 섬");

        assertThat(response.islandName()).isEqualTo("새로운 섬");
        assertThat(response.islandId()).isEqualTo(20L);
    }

    @Test
    void throwsWhenNeitherIslandIdNorNewNameGiven() {
        Scrap scrap = new Scrap("https://example.com", "제목", "본문", "본문",
            null, null, null, new float[]{0.1f, 0.2f});
        ReflectionTestUtils.setField(scrap, "id", 1L);
        when(scrapRepository.findById(1L)).thenReturn(Optional.of(scrap));

        assertThatThrownBy(() -> scrapConfirmService.confirm(1L, null, null))
            .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void throwsWhenScrapNotFound() {
        when(scrapRepository.findById(99L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> scrapConfirmService.confirm(99L, 10L, null))
            .isInstanceOf(EntityNotFoundException.class);
    }

}
