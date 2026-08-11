package com.worldengine.export.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import com.worldengine.export.dto.WorldExportResponse;
import com.worldengine.extraction.model.FallbackLevel;
import com.worldengine.extraction.model.SourceType;
import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.scrap.entity.Scrap;
import com.worldengine.scrap.repository.ScrapRepository;
import com.worldengine.topic.entity.Topic;
import com.worldengine.topic.repository.TopicRepository;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
public class ExportServiceTest {

    @Mock
    private IslandRepository islandRepository;

    @Mock
    private TopicRepository topicRepository;

    @Mock
    private ScrapRepository scrapRepository;

    @InjectMocks
    private ExportService exportService;

    @Test
    void exportsAllIslandsTopicsAndScraps() {
        Island island = new Island("여행", new float[]{0.1f});
        ReflectionTestUtils.setField(island, "id", 1L);
        island.assignCoordinate(3.0, 4.0);
        when(islandRepository.findAll()).thenReturn(List.of(island));

        Topic topic = new Topic("부산 관광", 1L);
        ReflectionTestUtils.setField(topic, "id", 2L);
        when(topicRepository.findAll()).thenReturn(List.of(topic));

        Scrap scrap = new Scrap("https://a.com", "제목", "본문", "요약",
            SourceType.ARTICLE, FallbackLevel.DIRECT_EXTRACTION, null, new float[]{0.2f});
        ReflectionTestUtils.setField(scrap, "id", 3L);
        scrap.confirmIsland(1L);
        when(scrapRepository.findAll()).thenReturn(List.of(scrap));

        WorldExportResponse result = exportService.export();

        assertThat(result.version()).isEqualTo(1);
        assertThat(result.islands()).hasSize(1);
        assertThat(result.islands().get(0).name()).isEqualTo("여행");
        assertThat(result.topics()).hasSize(1);
        assertThat(result.topics().get(0).name()).isEqualTo("부산 관광");
        assertThat(result.scraps()).hasSize(1);
        assertThat(result.scraps().get(0).url()).isEqualTo("https://a.com");
        assertThat(result.scraps().get(0).islandId()).isEqualTo(1L);
    }
}
