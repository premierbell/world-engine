package com.worldengine.topic.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.mockito.Mockito.verify;

import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.scrap.entity.Scrap;
import com.worldengine.scrap.repository.ScrapRepository;
import com.worldengine.topic.dto.TopicAddScrapsRequest;
import com.worldengine.topic.dto.TopicCreateRequest;
import com.worldengine.topic.dto.TopicCreateResponse;
import com.worldengine.topic.dto.TopicRenameRequest;
import com.worldengine.topic.dto.TopicRenameResponse;
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
class TopicServiceTest {

    @Mock
    private TopicRepository topicRepository;

    @Mock
    private IslandRepository islandRepository;

    @Mock
    private ScrapRepository scrapRepository;

    @InjectMocks
    private TopicService topicService;

    @Test
    void createsTopicAndAssignsScrapsToIt() {
        Island island = new Island("여행", new float[]{0.1f});
        ReflectionTestUtils.setField(island, "id", 1L);
        when(islandRepository.findById(1L)).thenReturn(Optional.of(island));

        Scrap a = new Scrap("https://a.com", "a", "본문", "요약", null, null, null, new float[]{0.1f});
        ReflectionTestUtils.setField(a, "id", 10L);
        Scrap b = new Scrap("https://b.com", "b", "본문", "요약", null, null, null, new float[]{0.1f});
        ReflectionTestUtils.setField(b, "id", 11L);
        when(scrapRepository.findAllById(List.of(10L, 11L))).thenReturn(List.of(a, b));

        when(topicRepository.save(any(Topic.class))).thenAnswer(invocation -> {
            Topic topic = invocation.getArgument(0);
            ReflectionTestUtils.setField(topic, "id", 100L);
            return topic;
        });

        TopicCreateResponse result = topicService.create(new TopicCreateRequest(1L, "부산 여행", List.of(10L, 11L)));

        assertThat(result.id()).isEqualTo(100L);
        assertThat(result.name()).isEqualTo("부산 여행");
        assertThat(result.scrapCount()).isEqualTo(2);
        assertThat(a.getTopicId()).isEqualTo(100L);
        assertThat(b.getTopicId()).isEqualTo(100L);
    }

    @Test
    void addsScrapsToExistingTopic() {
        Topic topic = new Topic("부산 해변", 1L);
        ReflectionTestUtils.setField(topic, "id", 5L);
        when(topicRepository.findById(5L)).thenReturn(Optional.of(topic));

        Scrap a = new Scrap("https://a.com", "a", "본문", "요약", null, null, null, new float[]{0.1f});
        ReflectionTestUtils.setField(a, "id", 10L);
        when(scrapRepository.findAllById(List.of(10L))).thenReturn(List.of(a));

        TopicCreateResponse result = topicService.addScraps(5L, new TopicAddScrapsRequest(List.of(10L)));

        assertThat(result.id()).isEqualTo(5L);
        assertThat(result.name()).isEqualTo("부산 해변");
        assertThat(result.scrapCount()).isEqualTo(1);
        assertThat(a.getTopicId()).isEqualTo(5L);
    }

    @Test
    void throwsWhenAddingScrapsToNonExistentTopic() {
        when(topicRepository.findById(99L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> topicService.addScraps(99L, new TopicAddScrapsRequest(List.of(1L))))
            .isInstanceOf(EntityNotFoundException.class);
    }

    @Test
    void throwsWhenIslandNotFound() {
        when(islandRepository.findById(99L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> topicService.create(new TopicCreateRequest(99L, "이름", List.of(1L))))
            .isInstanceOf(EntityNotFoundException.class);
    }

    @Test
    void renamesTopic() {
        Topic topic = new Topic("부산 해변", 1L);
        ReflectionTestUtils.setField(topic, "id", 5L);
        when(topicRepository.findById(5L)).thenReturn(Optional.of(topic));

        TopicRenameResponse result = topicService.rename(5L, new TopicRenameRequest("부산 여행 코스"));

        assertThat(result.id()).isEqualTo(5L);
        assertThat(result.name()).isEqualTo("부산 여행 코스");
        assertThat(topic.getName()).isEqualTo("부산 여행 코스");
    }

    @Test
    void throwsWhenRenamingToBlankName() {
        assertThatThrownBy(() -> topicService.rename(5L, new TopicRenameRequest(" ")))
            .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void throwsWhenRenamingNonExistentTopic() {
        when(topicRepository.findById(99L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> topicService.rename(99L, new TopicRenameRequest("이름")))
            .isInstanceOf(EntityNotFoundException.class);
    }

    @Test
    void deletesTopicAndUnassignsScraps() {
        Topic topic = new Topic("부산 해변", 1L);
        ReflectionTestUtils.setField(topic, "id", 5L);
        when(topicRepository.findById(5L)).thenReturn(Optional.of(topic));

        Scrap scrap = new Scrap("https://a.com", "a", "본문", "요약", null, null, null, new float[]{0.1f});
        scrap.assignTopic(5L);
        when(scrapRepository.findByTopicId(5L)).thenReturn(List.of(scrap));

        topicService.delete(5L);

        assertThat(scrap.getTopicId()).isNull();
        verify(scrapRepository).saveAll(List.of(scrap));
        verify(topicRepository).deleteById(5L);
    }

    @Test
    void throwsWhenDeletingNonExistentTopic() {
        when(topicRepository.findById(99L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> topicService.delete(99L))
            .isInstanceOf(EntityNotFoundException.class);
    }
}
