package com.worldengine.scrap.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.when;

import com.worldengine.scrap.dto.ScrapDetailResponse;
import com.worldengine.scrap.dto.ScrapSummaryResponse;
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
class ScrapQueryServiceTest {

    @Mock
    private ScrapRepository scrapRepository;

    @InjectMocks
    private ScrapQueryService scrapQueryService;

    @Test
    void listsAllScrapsAsSummaries() {
        Scrap scrap = new Scrap("https://example.com", "제목", "본문", "요약",
            null, null, null, new float[]{0.1f});
        ReflectionTestUtils.setField(scrap, "id", 1L);
        when(scrapRepository.findAll()).thenReturn(List.of(scrap));

        List<ScrapSummaryResponse> result = scrapQueryService.findAll();

        assertThat(result).hasSize(1);
        assertThat(result.get(0).title()).isEqualTo("제목");
    }

    @Test
    void findsScrapDetailById() {
        Scrap scrap = new Scrap("https://example.com", "제목", "본문", "요약",
            null, null, "메모", new float[]{0.1f});
        ReflectionTestUtils.setField(scrap, "id", 1L);
        when(scrapRepository.findById(1L)).thenReturn(Optional.of(scrap));

        ScrapDetailResponse result = scrapQueryService.findById(1L);

        assertThat(result.userContext()).isEqualTo("메모");
    }

    @Test
    void throwsWhenScrapNotFound() {
        when(scrapRepository.findById(99L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> scrapQueryService.findById(99L))
            .isInstanceOf(EntityNotFoundException.class);
    }
}
