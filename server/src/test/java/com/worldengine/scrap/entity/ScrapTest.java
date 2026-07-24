package com.worldengine.scrap.entity;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class ScrapTest {

    @Test
    void notCorrectedWhenConfirmedIslandMatchesRecommendation() {
        Scrap scrap = new Scrap("https://example.com", null, null, null, null, null, null, null);
        scrap.recordRecommendedIsland(1L);
        scrap.confirmIsland(1L);

        assertThat(scrap.wasCorrected()).isFalse();
    }

    @Test
    void correctedWhenConfirmedIslandDiffersFromRecommendation() {
        Scrap scrap = new Scrap("https://example.com", null, null, null, null, null, null, null);
        scrap.recordRecommendedIsland(1L);
        scrap.confirmIsland(2L);

        assertThat(scrap.wasCorrected()).isTrue();
    }

    @Test
    void notCorrectedWhenNoRecommendationExisted() {
        Scrap scrap = new Scrap("https://example.com", null, null, null, null, null, null, null);
        scrap.confirmIsland(1L);

        assertThat(scrap.wasCorrected()).isFalse();
    }
}