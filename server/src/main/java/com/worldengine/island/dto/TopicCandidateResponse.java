package com.worldengine.island.dto;

import com.worldengine.scrap.dto.ScrapSummaryResponse;
import java.util.List;

public record TopicCandidateResponse(
    List<ExistingTopicMatch> existingTopicMatches,
    List<TopicCandidateGroup> groups,
    List<ScrapSummaryResponse> ungrouped
) {}