package com.worldengine.island.service;

import com.worldengine.island.dto.IslandDetailResponse;
import com.worldengine.island.dto.IslandSummaryResponse;
import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.scrap.dto.ScrapSummaryResponse;
import com.worldengine.scrap.entity.Scrap;
import com.worldengine.scrap.repository.ScrapRepository;
import jakarta.persistence.EntityNotFoundException;
import java.util.List;
import org.springframework.stereotype.Service;

@Service
public class IslandQueryService {

    private final IslandRepository islandRepository;
    private final ScrapRepository scrapRepository;

    public IslandQueryService(IslandRepository islandRepository, ScrapRepository scrapRepository) {
        this.islandRepository = islandRepository;
        this.scrapRepository = scrapRepository;
    }

    public List<IslandSummaryResponse> findAll() {
        return islandRepository.findAll().stream()
            .map(island -> new IslandSummaryResponse(
                island.getId(), island.getName(), scrapRepository.countByIslandId(island.getId())))
            .toList();
    }

    public IslandDetailResponse findById(Long islandId) {
        Island island = islandRepository.findById(islandId)
            .orElseThrow(() -> new EntityNotFoundException("존재하지 않는 Island: " + islandId));

        List<ScrapSummaryResponse> scraps =
            scrapRepository.findByIslandId(islandId).stream()
                .map(this::toSummary)
                .toList();

        return new IslandDetailResponse(island.getId(), island.getName(), scraps);
    }

    private ScrapSummaryResponse toSummary(Scrap scrap) {
        return new ScrapSummaryResponse(scrap.getId(), scrap.getUrl(), scrap.getTitle(),
            scrap.getIslandId(), scrap.wasCorrected(), scrap.getCreatedAt());
    }
}
