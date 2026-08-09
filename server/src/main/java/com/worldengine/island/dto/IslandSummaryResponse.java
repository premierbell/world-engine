package com.worldengine.island.dto;

import com.worldengine.island.model.GrowthTier;
import java.util.List;

public record IslandSummaryResponse(
    Long id, String name, long scrapCount, long topicCount, Double x, Double y, GrowthTier tier, List<Long> topicIds
) {}