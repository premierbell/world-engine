package com.worldengine.island.service;

import com.worldengine.island.repository.IslandRepository;
import java.util.List;
import org.springframework.stereotype.Service;

/**
 * 신규 Island 생성 시 좌표를 배정한다 - CoordinateMigrationService(일괄
 * 마이그레이션)와 같은 NearestNeighborCoordinateStrategy를 재사용,
 * 이 서비스는 실시간 생성(ScrapConfirmService) 쪽 얇은 어댑터일 뿐이다.
 */
@Service
public class IslandCoordinateService {

    private final IslandRepository islandRepository;
    private final NearestNeighborCoordinateStrategy strategy;

    public IslandCoordinateService(IslandRepository islandRepository, NearestNeighborCoordinateStrategy strategy) {
        this.islandRepository = islandRepository;
        this.strategy = strategy;
    }

    public MapCoordinateService.Coordinate assignCoordinateForNewIsland(float[] embedding) {
        List<PlacedIsland> placed = islandRepository.findAll().stream()
            .filter(island -> island.getX() != null && island.getY() != null)
            .map(island -> new PlacedIsland(island.getX(), island.getY(), island.getEmbedding()))
            .toList();

        return strategy.calculate(embedding, placed);
    }
}
