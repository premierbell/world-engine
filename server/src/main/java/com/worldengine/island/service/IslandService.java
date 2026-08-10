package com.worldengine.island.service;

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
import org.springframework.stereotype.Service;

@Service
public class IslandService {

    private final IslandRepository islandRepository;
    private final TopicRepository topicRepository;
    private final ScrapRepository scrapRepository;

    public IslandService(
        IslandRepository islandRepository,
        TopicRepository topicRepository,
        ScrapRepository scrapRepository) {
        this.islandRepository = islandRepository;
        this.topicRepository = topicRepository;
        this.scrapRepository = scrapRepository;
    }

    public IslandRenameResponse rename(Long islandId, IslandRenameRequest request) {
        if (request.name() == null || request.name().isBlank()) {
            throw new IllegalArgumentException("이름은 비어있을 수 없음");
        }

        Island island = islandRepository.findById(islandId)
            .orElseThrow(() -> new EntityNotFoundException("존재하지 않는 Island: " + islandId));

        island.rename(request.name());
        islandRepository.save(island);

        return new IslandRenameResponse(island.getId(), island.getName());
    }

    /**
     * Island를 지우면 그 안의 Topic도 같이 지운다(Topic은 Island 없이는
     * 의미가 없음). 스크랩은 지우지 않고 islandId/topicId만 비워서
     * "정리할 스크랩" 목록으로 되돌린다 - 실수로 만든 Island를 지워도
     * 스크랩 자체는 잃지 않는다.
     */
    public void delete(Long islandId) {
        islandRepository.findById(islandId)
            .orElseThrow(() -> new EntityNotFoundException("존재하지 않는 Island: " + islandId));

        List<Scrap> scraps = scrapRepository.findByIslandId(islandId);
        for (Scrap scrap : scraps) {
            scrap.assignTopic(null);
            scrap.confirmIsland(null);
        }
        scrapRepository.saveAll(scraps);

        List<Topic> topics = topicRepository.findByIslandId(islandId);
        topicRepository.deleteAll(topics);

        islandRepository.deleteById(islandId);
    }

}
