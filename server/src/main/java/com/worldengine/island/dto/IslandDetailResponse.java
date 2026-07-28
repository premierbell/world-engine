package com.worldengine.island.dto;

import com.worldengine.scrap.dto.ScrapSummaryResponse;
import java.util.List;

public record IslandDetailResponse(
    Long id,
    String name,
    List<ScrapSummaryResponse> scraps,
    Double cosineVariance,
    Double overrideRate
) {}
