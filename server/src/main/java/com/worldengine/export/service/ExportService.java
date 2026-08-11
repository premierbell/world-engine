package com.worldengine.export.service;

import com.worldengine.export.dto.IslandExport;
import com.worldengine.export.dto.ScrapExport;
import com.worldengine.export.dto.TopicExport;
import com.worldengine.export.dto.WorldExportResponse;
import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.scrap.entity.Scrap;
import com.worldengine.scrap.repository.ScrapRepository;
import com.worldengine.topic.entity.Topic;
import com.worldengine.topic.repository.TopicRepository;
import java.time.Instant;
import java.util.List;
import org.springframework.stereotype.Service;

/**
 * "내 세계 내보내기" - 전체 데이터를 JSON 스냅샷으로 뽑기만 한다.
 * Import는 아직 안 만듦(필요해지는 시점에 추가 - docs 로드맵 ③단계는
 * Export까지만).
 */
@Service
public class ExportService {

    private static final int EXPORT_VERSION = 1;

    private final IslandRepository islandRepository;
    private final TopicRepository topicRepository;
    private final ScrapRepository scrapRepository;

    public ExportService(
        IslandRepository islandRepository,
        TopicRepository topicRepository,
        ScrapRepository scrapRepository) {
        this.islandRepository = islandRepository;
        this.topicRepository = topicRepository;
        this.scrapRepository = scrapRepository;
    }

    public WorldExportResponse export() {
        List<IslandExport> islands = islandRepository.findAll().stream()
            .map(this::toIslandExport)
            .toList();

        List<TopicExport> topics = topicRepository.findAll().stream()
            .map(this::toTopicExport)
            .toList();

        List<ScrapExport> scraps = scrapRepository.findAll().stream()
            .map(this::toScrapExport)
            .toList();

        return new WorldExportResponse(Instant.now(), EXPORT_VERSION, islands, topics, scraps);
    }

    private IslandExport toIslandExport(Island island) {
        return new IslandExport(island.getId(), island.getName(), island.getX(), island.getY(), island.getEmbedding());
    }

    private TopicExport toTopicExport(Topic topic) {
        return new TopicExport(topic.getId(), topic.getIslandId(), topic.getName(), topic.getCreatedAt());
    }

    private ScrapExport toScrapExport(Scrap scrap) {
        return new ScrapExport(
            scrap.getId(),
            scrap.getUrl(),
            scrap.getTitle(),
            scrap.getContent(),
            scrap.getSummary(),
            scrap.getSourceType(),
            scrap.getFallbackLevel(),
            scrap.getFailureReason(),
            scrap.getUserContext(),
            scrap.getIslandId(),
            scrap.getTopicId(),
            scrap.getRecommendedIslandId(),
            scrap.getCreatedAt(),
            scrap.getEmbedding()
        );
    }
}
