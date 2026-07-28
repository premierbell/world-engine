package com.worldengine.island.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;
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

    @Test
    void computesCosineVarianceAcrossScrapsInIsland() {
        Island island = new Island("여행", new float[]{0.1f});
        ReflectionTestUtils.setField(island, "id", 1L);

        Scrap a = new Scrap("https://a.com", "a", "본문", "요약", null, null, null, new float[]{1f, 0f});
        Scrap b = new Scrap("https://b.com", "b", "본문", "요약", null, null, null, new float[]{1f, 0f});
        Scrap c = new Scrap("https://c.com", "c", "본문", "요약", null, null, null, new float[]{0f, 1f});

        when(islandRepository.findById(1L)).thenReturn(Optional.of(island));
        when(scrapRepository.findByIslandId(1L)).thenReturn(List.of(a, b, c));

        IslandDetailResponse result = islandQueryService.findById(1L);

        assertThat(result.cosineVariance()).isCloseTo(0.222, within(0.01));
    }

    @Test
    void returnsNullCosineVarianceWhenFewerThanTwoScraps() {
        Island island = new Island("여행", new float[]{0.1f});
        ReflectionTestUtils.setField(island, "id", 1L);
        Scrap a = new Scrap("https://a.com", "a", "본문", "요약", null, null, null, new float[]{1f, 0f});

        when(islandRepository.findById(1L)).thenReturn(Optional.of(island));
        when(scrapRepository.findByIslandId(1L)).thenReturn(List.of(a));

        IslandDetailResponse result = islandQueryService.findById(1L);

        assertThat(result.cosineVariance()).isNull();
    }

    @Test
    void computesOverrideRateFromRecommendationHistory() {
        Island island = new Island("여행", new float[]{0.1f});
        ReflectionTestUtils.setField(island, "id", 1L);

        Scrap accepted = new Scrap("https://a.com", "a", "본문", "요약", null, null, null,
            new float[]{1f, 0f});
        accepted.confirmIsland(1L);
        accepted.recordRecommendedIsland(1L);

        Scrap overridden = new Scrap("https://b.com", "b", "본문", "요약", null, null, null,
            new float[]{1f, 0f});
        overridden.confirmIsland(1L);
        overridden.recordRecommendedIsland(2L);

        Scrap coldStart = new Scrap("https://c.com", "c", "본문", "요약", null, null, null,
            new float[]{1f, 0f});
        coldStart.confirmIsland(1L);

        when(islandRepository.findById(1L)).thenReturn(Optional.of(island));
        when(scrapRepository.findByIslandId(1L)).thenReturn(
            List.of(accepted, overridden, coldStart));

        IslandDetailResponse result = islandQueryService.findById(1L);

        assertThat(result.overrideRate()).isEqualTo(0.5);
    }

    @Test
    void returnsNullOverrideRateWhenNoRecommendationHistory() {
        Island island = new Island("여행", new float[]{0.1f});
        ReflectionTestUtils.setField(island, "id", 1L);
        Scrap coldStart = new Scrap("https://a.com", "a", "본문", "요약", null, null, null, new float[]{1f, 0f});
        coldStart.confirmIsland(1L);

        when(islandRepository.findById(1L)).thenReturn(Optional.of(island));
        when(scrapRepository.findByIslandId(1L)).thenReturn(List.of(coldStart));

        IslandDetailResponse result = islandQueryService.findById(1L);

        assertThat(result.overrideRate()).isNull();
    }
}
