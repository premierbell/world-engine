package com.worldengine.export.dto;

import java.time.Instant;

public record TopicExport(
    Long id,
    Long islandId,
    String name,
    Instant createdAt
) {}
