package com.worldengine.topic.service;

import com.worldengine.recommendation.client.TopicNameSuggestionClient;
import com.worldengine.scrap.entity.Scrap;
import com.worldengine.scrap.repository.ScrapRepository;
import com.worldengine.topic.dto.TopicNameSuggestionRequest;
import com.worldengine.topic.dto.TopicNameSuggestionResponse;
import java.util.List;
import org.springframework.stereotype.Service;

/**
 * "AI는 제안만, 이름 확정은 사용자가"(docs/v2_design.md와 같은 원칙) -
 * 스크랩 요약을 보고 이름 하나를 제안만 하고, 실제 Topic 생성(POST
 * /api/topics)은 그대로 사용자가 입력창을 확인/수정한 뒤 별도로 호출한다.
 * 이 서비스는 아무것도 저장하지 않는다.
 */
@Service
public class TopicNamingService {

    private final ScrapRepository scrapRepository;
    private final TopicNameSuggestionClient topicNameSuggestionClient;

    public TopicNamingService(
        ScrapRepository scrapRepository,
        TopicNameSuggestionClient topicNameSuggestionClient) {
        this.scrapRepository = scrapRepository;
        this.topicNameSuggestionClient = topicNameSuggestionClient;
    }

    public TopicNameSuggestionResponse suggestName(TopicNameSuggestionRequest request) {
        if (request.scrapIds() == null || request.scrapIds().isEmpty()) {
            throw new IllegalArgumentException("scrapIds는 비어있을 수 없음");
        }

        List<String> summaries = scrapRepository.findAllById(request.scrapIds()).stream()
            .map(Scrap::getSummary)
            .filter(summary -> summary != null && !summary.isBlank())
            .toList();

        if (summaries.isEmpty()) {
            throw new IllegalArgumentException("요약이 있는 스크랩이 없어서 이름을 제안할 수 없음");
        }

        String name = topicNameSuggestionClient.suggestName(summaries);
        return new TopicNameSuggestionResponse(name);
    }
}
