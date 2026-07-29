package com.worldengine.topic.dto;

public record TopicCreateResponse(Long id, String name, Long islandId, int scrapCount) {}