package com.worldengine.topic.dto;

import com.worldengine.scrap.dto.ScrapSummaryResponse;
import java.util.List;

public record TopicSummaryResponse(Long id, String name, List<ScrapSummaryResponse> scraps) {}
