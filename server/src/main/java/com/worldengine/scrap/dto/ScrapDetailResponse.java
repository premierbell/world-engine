package com.worldengine.scrap.dto;

import com.worldengine.extraction.model.FallbackLevel;
import com.worldengine.extraction.model.SourceType;
import java.time.Instant;

public record ScrapDetailResponse(
    Long id,
    String url,
    String title,
    String summary,
    SourceType sourceType,
    FallbackLevel fallbackLevel,
    String userContext,
    Long islandId,
    Instant createdAt
) {}
