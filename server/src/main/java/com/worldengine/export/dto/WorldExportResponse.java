package com.worldengine.export.dto;

import java.time.Instant;
import java.util.List;

public record WorldExportResponse(
    Instant exportedAt,
    int version,
    List<IslandExport> islands,
    List<TopicExport> topics,
    List<ScrapExport> scraps
) {}
