package com.worldengine.scrap.dto;

import com.worldengine.extraction.model.ExtractionStatus;
import com.worldengine.extraction.model.FailureReason;
import com.worldengine.recommendation.service.IslandRecommendation;
import java.util.List;

public record ScrapCreateResponse(
    Long scrapId,
    String title,
    ExtractionStatus status,
    FailureReason failureReason,
    List<IslandRecommendation> recommendations,
    boolean duplicate,
    Long existingIslandId,
    String existingIslandName
) {}
