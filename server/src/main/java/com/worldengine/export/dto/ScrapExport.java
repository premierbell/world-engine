package com.worldengine.export.dto;

import com.worldengine.extraction.model.FailureReason;
import com.worldengine.extraction.model.FallbackLevel;
import com.worldengine.extraction.model.SourceType;
import java.time.Instant;

public record ScrapExport(
    Long id,
    String url,
    String title,
    String content,
    String summary,
    SourceType sourceType,
    FallbackLevel fallbackLevel,
    FailureReason failureReason,
    String userContext,
    Long islandId,
    Long topicId,
    Long recommendedIslandId,
    Instant createdAt,
    float[] embedding
) {}
