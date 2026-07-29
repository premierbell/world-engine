package com.worldengine.island.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;
import static org.mockito.Mockito.when;

import com.worldengine.island.dto.TopicCandidateGroup;
import com.worldengine.island.dto.TopicCandidateResponse;
import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.recommendation.client.LlmPairwiseJudgeClient;
import com.worldengine.scrap.entity.Scrap;
import com.worldengine.scrap.repository.ScrapRepository;
import jakarta.persistence.EntityNotFoundException;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class TopicCandidateServiceTest {

    @Mock
    private IslandRepository islandRepository;

    @Mock
    private ScrapRepository scrapRepository;

    @Mock
    private LlmPairwiseJudgeClient llmPairwiseJudgeClient;

    private Scrap scrap(Long id, String summary) {
        Scrap scrap = new Scrap("https://example.com/" + id, "제목" + id, "본문", summary,
            null, null, null, new float[]{0.1f});
        ReflectionTestUtils.setField(scrap, "id", id);
        return scrap;
    }

    @Test
    void connectedComponentsChainsThroughIndirectMatches() {
        Island island = new Island("여행", new float[]{0.1f});
        ReflectionTestUtils.setField(island, "id", 1L);
        Scrap a = scrap(1L, "A");
        Scrap b = scrap(2L, "B");
        Scrap c = scrap(3L, "C");

        when(islandRepository.findById(1L)).thenReturn(Optional.of(island));
        when(scrapRepository.findByIslandId(1L)).thenReturn(List.of(a, b, c));
        when(llmPairwiseJudgeClient.scoreMechanism("A", "B")).thenReturn(0.9);
        when(llmPairwiseJudgeClient.scoreMechanism("A", "C")).thenReturn(0.0);
        when(llmPairwiseJudgeClient.scoreMechanism("B", "C")).thenReturn(0.9);

        TopicCandidateService service = new TopicCandidateService(
            islandRepository, scrapRepository, llmPairwiseJudgeClient, new ConnectedComponentsGrouping());

        TopicCandidateResponse result = service.generateCandidates(1L);

        assertThat(result.groups()).hasSize(1);
        TopicCandidateGroup group = result.groups().get(0);
        assertThat(group.scraps()).hasSize(3);
        assertThat(group.averageScore()).isCloseTo(0.6, within(0.01));
        assertThat(group.minimumScore()).isEqualTo(0.0);
        assertThat(result.ungrouped()).isEmpty();
    }

    @Test
    void cliqueSafeAvoidsChainingThroughIndirectMatches() {
        Island island = new Island("여행", new float[]{0.1f});
        ReflectionTestUtils.setField(island, "id", 1L);
        Scrap a = scrap(1L, "A");
        Scrap b = scrap(2L, "B");
        Scrap c = scrap(3L, "C");

        when(islandRepository.findById(1L)).thenReturn(Optional.of(island));
        when(scrapRepository.findByIslandId(1L)).thenReturn(List.of(a, b, c));
        when(llmPairwiseJudgeClient.scoreMechanism("A", "B")).thenReturn(0.9);
        when(llmPairwiseJudgeClient.scoreMechanism("A", "C")).thenReturn(0.0);
        when(llmPairwiseJudgeClient.scoreMechanism("B", "C")).thenReturn(0.9);

        TopicCandidateService service = new TopicCandidateService(
            islandRepository, scrapRepository, llmPairwiseJudgeClient, new CliqueSafeGrouping());

        TopicCandidateResponse result = service.generateCandidates(1L);

        assertThat(result.groups()).hasSize(1);
        TopicCandidateGroup group = result.groups().get(0);
        assertThat(group.scraps()).hasSize(2);
        assertThat(group.averageScore()).isCloseTo(0.9, within(0.01));
        assertThat(group.minimumScore()).isCloseTo(0.9, within(0.01));
        assertThat(result.ungrouped()).hasSize(1);
    }

    @Test
    void leavesScrapsBelowThresholdUngrouped() {
        Island island = new Island("여행", new float[]{0.1f});
        ReflectionTestUtils.setField(island, "id", 1L);
        Scrap a = scrap(1L, "A");
        Scrap b = scrap(2L, "B");

        when(islandRepository.findById(1L)).thenReturn(Optional.of(island));
        when(scrapRepository.findByIslandId(1L)).thenReturn(List.of(a, b));
        when(llmPairwiseJudgeClient.scoreMechanism("A", "B")).thenReturn(0.3);

        TopicCandidateService service = new TopicCandidateService(
            islandRepository, scrapRepository, llmPairwiseJudgeClient, new CliqueSafeGrouping());

        TopicCandidateResponse result = service.generateCandidates(1L);

        assertThat(result.groups()).isEmpty();
        assertThat(result.ungrouped()).hasSize(2);
    }

    @Test
    void throwsWhenIslandNotFound() {
        when(islandRepository.findById(99L)).thenReturn(Optional.empty());

        TopicCandidateService service = new TopicCandidateService(
            islandRepository, scrapRepository, llmPairwiseJudgeClient, new CliqueSafeGrouping());

        assertThatThrownBy(() -> service.generateCandidates(99L))
            .isInstanceOf(EntityNotFoundException.class);
    }
}
