package com.worldengine.island.dto;

public record IslandSummaryResponse(Long id, String name, long scrapCount, long topicCount, Double x, Double y) {}