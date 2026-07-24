package com.worldengine.scrap.dto;

import java.time.Instant;

public record ScrapSummaryResponse(Long id, String url, String title, Long islandId, Instant createdAt) {}
