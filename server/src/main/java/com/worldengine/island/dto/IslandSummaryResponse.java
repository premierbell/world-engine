package com.worldengine.island.dto;

import com.worldengine.island.model.GrowthTier;

public record IslandSummaryResponse(
    Long id, String name, long scrapCount, long topicCount, Double x, Double y, GrowthTier tier
) {}