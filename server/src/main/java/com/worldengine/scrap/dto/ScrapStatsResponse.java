package com.worldengine.scrap.dto;

public record ScrapStatsResponse(
    long totalScraps,
    long confirmedScraps,
    long unconfirmedScraps,
    long recommendationAcceptedCount,
    long recommendationOverriddenCount,
    long coldStartConfirmedCount,
    Double acceptanceRate,
    Double overrideRate
) {}
