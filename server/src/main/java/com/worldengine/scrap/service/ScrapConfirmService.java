package com.worldengine.scrap.service;

import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.scrap.dto.ScrapConfirmResponse;
import com.worldengine.scrap.entity.Scrap;
import com.worldengine.scrap.repository.ScrapRepository;
import jakarta.persistence.EntityNotFoundException;
import org.springframework.stereotype.Service;

@Service
public class ScrapConfirmService {

    private final ScrapRepository scrapRepository;
    private final IslandRepository islandRepository;

    public ScrapConfirmService(ScrapRepository scrapRepository, IslandRepository islandRepository) {
        this.scrapRepository = scrapRepository;
        this.islandRepository = islandRepository;
    }

    public ScrapConfirmResponse confirm(Long scrapId, Long islandId, String newIslandName) {
        Scrap scrap = scrapRepository.findById(scrapId)
            .orElseThrow(() -> new EntityNotFoundException("존재하지 않는 스크랩: " + scrapId));

        Island island = resolveIsland(scrap, islandId, newIslandName);

        scrap.confirmIsland(island.getId());
        scrapRepository.save(scrap);

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
        return islandRepository.save(newIsland);
    }
}
