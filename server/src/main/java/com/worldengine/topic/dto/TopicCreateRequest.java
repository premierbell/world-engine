package com.worldengine.topic.dto;

import java.util.List;

public record TopicCreateRequest(Long islandId, String name, List<Long> scrapIds) {}
