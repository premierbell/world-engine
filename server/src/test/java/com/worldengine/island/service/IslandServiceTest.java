package com.worldengine.island.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.worldengine.island.dto.IslandRenameRequest;
import com.worldengine.island.dto.IslandRenameResponse;
import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.scrap.entity.Scrap;
import com.worldengine.scrap.repository.ScrapRepository;
import com.worldengine.topic.entity.Topic;
import com.worldengine.topic.repository.TopicRepository;
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
class IslandServiceTest {

    @Mock
    private IslandRepository islandRepository;

    @Mock
    private TopicRepository topicRepository;

    @Mock
    private ScrapRepository scrapRepository;

    @InjectMocks
    private IslandService islandService;

    @Test
    void renamesIsland() {
        Island island = new Island("여행", new float[]{0.1f});
        ReflectionTestUtils.setField(island, "id", 1L);
        when(islandRepository.findById(1L)).thenReturn(Optional.of(island));

        IslandRenameResponse result = islandService.rename(1L, new IslandRenameRequest("부산 여행"));

        assertThat(result.id()).isEqualTo(1L);
        assertThat(result.name()).isEqualTo("부산 여행");
        assertThat(island.getName()).isEqualTo("부산 여행");
    }

    @Test
    void throwsWhenRenamingToBlankName() {
        assertThatThrownBy(() -> islandService.rename(1L, new IslandRenameRequest("  ")))
            .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void throwsWhenRenamingNonExistentIsland() {
        when(islandRepository.findById(99L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> islandService.rename(99L, new IslandRenameRequest("이름")))
            .isInstanceOf(EntityNotFoundException.class);
    }

    @Test
    void deletesIslandAndUnassignsScrapsAndTopics() {
        Island island = new Island("여행", new float[]{0.1f});
        ReflectionTestUtils.setField(island, "id", 1L);
        when(islandRepository.findById(1L)).thenReturn(Optional.of(island));

        Scrap scrap = new Scrap("https://a.com", "a", "본문", "요약", null, null, null, new float[]{0.1f});
        scrap.confirmIsland(1L);
        scrap.assignTopic(5L);
        when(scrapRepository.findByIslandId(1L)).thenReturn(List.of(scrap));

        Topic topic = new Topic("부산 여행", 1L);
        ReflectionTestUtils.setField(topic, "id", 5L);
        when(topicRepository.findByIslandId(1L)).thenReturn(List.of(topic));

        islandService.delete(1L);

        assertThat(scrap.getIslandId()).isNull();
        assertThat(scrap.getTopicId()).isNull();
        verify(scrapRepository).saveAll(List.of(scrap));
        verify(topicRepository).deleteAll(List.of(topic));
        verify(islandRepository).deleteById(1L);
    }

    @Test
    void throwsWhenDeletingNonExistentIsland() {
        when(islandRepository.findById(99L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> islandService.delete(99L))
            .isInstanceOf(EntityNotFoundException.class);
    }
}
