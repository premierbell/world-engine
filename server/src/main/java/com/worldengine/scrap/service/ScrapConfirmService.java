package com.worldengine.scrap.service;

import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.island.service.IslandCoordinateService;
import com.worldengine.island.service.IslandEmbeddingService;
import com.worldengine.island.service.MapCoordinateService;
import com.worldengine.scrap.dto.ScrapConfirmResponse;
import com.worldengine.scrap.entity.Scrap;
import com.worldengine.scrap.repository.ScrapRepository;
import jakarta.persistence.EntityNotFoundException;
import org.springframework.stereotype.Service;

@Service
public class ScrapConfirmService {

    private final ScrapRepository scrapRepository;
    private final IslandRepository islandRepository;
    private final IslandCoordinateService islandCoordinateService;
    private final IslandEmbeddingService islandEmbeddingService;

    public ScrapConfirmService(
        ScrapRepository scrapRepository,
        IslandRepository islandRepository,
        IslandCoordinateService islandCoordinateService,
        IslandEmbeddingService islandEmbeddingService) {
        this.scrapRepository = scrapRepository;
        this.islandRepository = islandRepository;
        this.islandCoordinateService = islandCoordinateService;
        this.islandEmbeddingService = islandEmbeddingService;
    }

    public ScrapConfirmResponse confirm(Long scrapId, Long islandId, String newIslandName) {
        Scrap scrap = scrapRepository.findById(scrapId)
            .orElseThrow(() -> new EntityNotFoundException("존재하지 않는 스크랩: " + scrapId));

        Long previousIslandId = scrap.getIslandId();
        Island island = resolveIsland(scrap, islandId, newIslandName);

        scrap.confirmIsland(island.getId());
        scrapRepository.save(scrap);

        // 멤버가 바뀌었으니 섬 대표 벡터(멤버 평균)를 다시 계산 - 다른 섬에서 옮겨 온 경우 이전 섬도
        islandEmbeddingService.refresh(island.getId());
        if (previousIslandId != null && !previousIslandId.equals(island.getId())) {
            islandEmbeddingService.refresh(previousIslandId);
        }

        return new ScrapConfirmResponse(scrap.getId(), island.getId(), island.getName());
    }

    private Island resolveIsland(Scrap scrap, Long islandId, String newIslandName) {
        boolean hasExisting = islandId != null;
        boolean hasNew = newIslandName != null && !newIslandName.isBlank();

        if (hasExisting == hasNew) {
            throw new IllegalArgumentException("islandId와 newIslandName 중 하나만 지정해야 함");
        }

        if (hasExisting) {
            return islandRepository.findById(islandId)
                .orElseThrow(() -> new EntityNotFoundException("존재하지 않는 Island: " + islandId));
        }

        Island newIsland = new Island(newIslandName, scrap.getEmbedding());
        MapCoordinateService.Coordinate coordinate = islandCoordinateService.assignCoordinateForNewIsland(scrap.getEmbedding());
        newIsland.assignCoordinate(coordinate.x(), coordinate.y());
        return islandRepository.save(newIsland);
    }
}
