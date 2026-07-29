package com.worldengine.topic.service;

import com.worldengine.island.repository.IslandRepository;
import com.worldengine.scrap.entity.Scrap;
import com.worldengine.scrap.repository.ScrapRepository;
import com.worldengine.topic.dto.TopicCreateRequest;
import com.worldengine.topic.dto.TopicCreateResponse;
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

}
