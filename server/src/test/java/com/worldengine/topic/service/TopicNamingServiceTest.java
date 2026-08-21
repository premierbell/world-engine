package com.worldengine.topic.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.when;

import com.worldengine.recommendation.client.TopicNameSuggestionClient;
import com.worldengine.scrap.entity.Scrap;
import com.worldengine.scrap.repository.ScrapRepository;
import com.worldengine.topic.dto.TopicNameSuggestionRequest;
import com.worldengine.topic.dto.TopicNameSuggestionResponse;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class TopicNamingServiceTest {

    @Mock
    private ScrapRepository scrapRepository;

    @Mock
    private TopicNameSuggestionClient topicNameSuggestionClient;

    @InjectMocks
    private TopicNamingService topicNamingService;

    @Test
    void suggestsNameFromScrapSummaries() {
        Scrap a = new Scrap("https://a.com", "a", "본문", "부산 해변 여행기", null, null, null, new float[]{0.1f});
        ReflectionTestUtils.setField(a, "id", 1L);
        Scrap b = new Scrap("https://b.com", "b", "본문", "제주 해변 맛집", null, null, null, new float[]{0.1f});
        ReflectionTestUtils.setField(b, "id", 2L);

        when(scrapRepository.findAllById(List.of(1L, 2L))).thenReturn(List.of(a, b));
        when(topicNameSuggestionClient.suggestName(List.of("부산 해변 여행기", "제주 해변 맛집")))
            .thenReturn("해변 여행");

        TopicNameSuggestionResponse result =
            topicNamingService.suggestName(new TopicNameSuggestionRequest(List.of(1L, 2L)));

        assertThat(result.name()).isEqualTo("해변 여행");
    }

    @Test
    void throwsWhenScrapIdsEmpty() {
        assertThatThrownBy(() -> topicNamingService.suggestName(new TopicNameSuggestionRequest(List.of())))
            .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void throwsWhenNoScrapsHaveSummary() {
        Scrap noSummary = new Scrap("https://a.com", "a", "본문", null, null, null, null, new float[]{0.1f});
        ReflectionTestUtils.setField(noSummary, "id", 1L);
        when(scrapRepository.findAllById(List.of(1L))).thenReturn(List.of(noSummary));

        assertThatThrownBy(() -> topicNamingService.suggestName(new TopicNameSuggestionRequest(List.of(1L))))
            .isInstanceOf(IllegalArgumentException.class);
    }
}
