package com.worldengine.island.dto;

import com.worldengine.scrap.dto.ScrapSummaryResponse;

public record ExistingTopicMatch(
    ScrapSummaryResponse scrap,
    Long topicId,
    String topicName,
    double score,
    ScrapSummaryResponse matchedAgainst
) {}
