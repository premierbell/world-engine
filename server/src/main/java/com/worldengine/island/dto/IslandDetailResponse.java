package com.worldengine.island.dto;

import com.worldengine.scrap.dto.ScrapSummaryResponse;
import com.worldengine.topic.dto.TopicSummaryResponse;
import java.util.List;

public record IslandDetailResponse(
    Long id,
    String name,
    List<ScrapSummaryResponse> scraps,
    Double cosineVariance,
    Double overrideRate,
    List<TopicSummaryResponse> topics
) {}
