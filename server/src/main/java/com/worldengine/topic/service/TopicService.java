package com.worldengine.topic.service;

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
import org.springframework.stereotype.Service;

@Service
public class TopicService {

    private final TopicRepository topicRepository;
    private final IslandRepository islandRepository;
    private final ScrapRepository scrapRepository;

    public TopicService(
        TopicRepository topicRepository,
        IslandRepository islandRepository,
        ScrapRepository scrapRepository) {
        this.topicRepository = topicRepository;
        this.islandRepository = islandRepository;
        this.scrapRepository = scrapRepository;
    }

    public TopicCreateResponse create(TopicCreateRequest request) {
        islandRepository.findById(request.islandId())
            .orElseThrow(() -> new EntityNotFoundException("존재하지 않는 Island: " + request.islandId()));

        Topic topic = topicRepository.save(new Topic(request.name(), request.islandId()));

        List<Scrap> scraps = scrapRepository.findAllById(request.scrapIds());
        for (Scrap scrap : scraps) {
            scrap.assignTopic(topic.getId());
        }
        scrapRepository.saveAll(scraps);

        return new TopicCreateResponse(topic.getId(), topic.getName(), topic.getIslandId(), scraps.size());
    }

    public TopicCreateResponse addScraps(Long topicId, TopicAddScrapsRequest request) {
        Topic topic = topicRepository.findById(topicId)
            .orElseThrow(() -> new EntityNotFoundException("존재하지 않는 Topic: " + topicId));

        List<Scrap> scraps = scrapRepository.findAllById(request.scrapIds());
        for (Scrap scrap : scraps) {
            scrap.assignTopic(topic.getId());
        }
        scrapRepository.saveAll(scraps);

        return new TopicCreateResponse(topic.getId(), topic.getName(), topic.getIslandId(), scraps.size());
    }

    public TopicRenameResponse rename(Long topicId, TopicRenameRequest request) {
        if (request.name() == null || request.name().isBlank()) {
            throw new IllegalArgumentException("이름은 비어있을 수 없음");
        }

        Topic topic = topicRepository.findById(topicId)
            .orElseThrow(() -> new EntityNotFoundException("존재하지 않는 Topic: " + topicId));

        topic.rename(request.name());
        topicRepository.save(topic);

        return new TopicRenameResponse(topic.getId(), topic.getName());
    }

    /**
     * Topic을 지워도 스크랩은 안 지운다 - topicId만 비워서 Island 안에서
     * "아직 Topic으로 안 나뉜" 상태로 되돌린다(Island 삭제 때와 같은 원칙).
     */
    public void delete(Long topicId) {
        topicRepository.findById(topicId)
            .orElseThrow(() -> new EntityNotFoundException("존재하지 않는 Topic: " + topicId));

        List<Scrap> scraps = scrapRepository.findByTopicId(topicId);
        for (Scrap scrap : scraps) {
            scrap.assignTopic(null);
        }
        scrapRepository.saveAll(scraps);

        topicRepository.deleteById(topicId);
    }
}
