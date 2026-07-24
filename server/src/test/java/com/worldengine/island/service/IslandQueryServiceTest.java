package com.worldengine.island.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.when;

import com.worldengine.island.dto.IslandDetailResponse;
import com.worldengine.island.dto.IslandSummaryResponse;
import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.scrap.entity.Scrap;
import com.worldengine.scrap.repository.ScrapRepository;
import jakarta.persistence.EntityNotFoundException;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class IslandQueryServiceTest {

    @Mock
    private IslandRepository islandRepository;

    @Mock
    private ScrapRepository scrapRepository;

    @InjectMocks
    private IslandQueryService islandQueryService;

    @Test
    void listsAllIslandsWithScrapCount() {
        Island island = new Island("다이어트", new float[]{0.1f});
        ReflectionTestUtils.setField(island, "id", 1L);
        when(islandRepository.findAll()).thenReturn(List.of(island));
        when(scrapRepository.countByIslandId(1L)).thenReturn(3L);

        List<IslandSummaryResponse> result = islandQueryService.findAll();

        assertThat(result).hasSize(1);
        assertThat(result.get(0).scrapCount()).isEqualTo(3L);
    }

    @Test
    void findsIslandDetailWithScraps() {
        Island island = new Island("다이어트", new float[]{0.1f});
        ReflectionTestUtils.setField(island, "id", 1L);
        Scrap scrap = new Scrap("https://example.com", "제목", "본문", "요약",
            null, null, null, new float[]{0.1f});
        ReflectionTestUtils.setField(scrap, "id", 5L);

        when(islandRepository.findById(1L)).thenReturn(Optional.of(island));
        when(scrapRepository.findByIslandId(1L)).thenReturn(List.of(scrap));

        IslandDetailResponse result = islandQueryService.findById(1L);

        assertThat(result.scraps()).hasSize(1);
        assertThat(result.scraps().get(0).id()).isEqualTo(5L);
    }

    @Test
    void throwsWhenIslandNotFound() {
        when(islandRepository.findById(99L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> islandQueryService.findById(99L))
            .isInstanceOf(EntityNotFoundException.class);
    }
}
