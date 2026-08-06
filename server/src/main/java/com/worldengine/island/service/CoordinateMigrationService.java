package com.worldengine.island.service;

import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import java.util.ArrayList;
import java.util.List;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

/**
 * 좌표가 NULL인 Island를 id 순으로 순회하며 NearestNeighborCoordinateStrategy로
 * 좌표를 채운다. "한 번 쓰고 버릴 스크립트"가 아니라 영구 서비스 -
 * 신규 Island 생성(ScrapConfirmService)도 같은 전략을 재사용하고,
 * 이 서비스는 여러 Island에 대해 그걸 반복 호출하는 것뿐이다.
 * docs/map_home_redesign.md "마이그레이션 설계" 참고.
 */
@Slf4j
@Service
public class CoordinateMigrationService {

    private final IslandRepository islandRepository;
    private final NearestNeighborCoordinateStrategy strategy;

    public CoordinateMigrationService(IslandRepository islandRepository, NearestNeighborCoordinateStrategy strategy) {
        this.islandRepository = islandRepository;
        this.strategy = strategy;
    }

    public void migrateAll(boolean dryRun) {
        List<Island> islands = islandRepository.findAll(Sort.by("id"));

        List<PlacedIsland> placed = new ArrayList<>();
        for (Island island : islands) {
            if (island.getX() != null && island.getY() != null) {
                placed.add(new PlacedIsland(island.getX(), island.getY(), island.getEmbedding()));
            }
        }

        for (Island island : islands) {
            if (island.getX() != null && island.getY() != null) {
                continue;
            }

            MapCoordinateService.Coordinate coordinate = strategy.calculate(island.getEmbedding(), placed);

            log.info("migrateAll dryRun={} island={}({}) -> ({}, {})",
                dryRun, island.getId(), island.getName(), coordinate.x(), coordinate.y());

            if (!dryRun) {
                island.assignCoordinate(coordinate.x(), coordinate.y());
                islandRepository.save(island);
            }

            placed.add(new PlacedIsland(coordinate.x(), coordinate.y(), island.getEmbedding()));
        }
    }
}
