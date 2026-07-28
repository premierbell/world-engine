package com.worldengine.island.dto;

import com.worldengine.scrap.dto.ScrapSummaryResponse;
import java.util.List;

public record TopicCandidateGroup(List<ScrapSummaryResponse> scraps, double averageScore, double minimumScore) {}
