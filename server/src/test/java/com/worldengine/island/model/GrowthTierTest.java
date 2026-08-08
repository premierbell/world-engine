package com.worldengine.island.model;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class GrowthTierTest {

    @Test
    void mapsBoundaryValuesToExpectedTiers() {
        assertThat(GrowthTier.fromScrapCount(1)).isEqualTo(GrowthTier.SEED);
        assertThat(GrowthTier.fromScrapCount(3)).isEqualTo(GrowthTier.SEED);
        assertThat(GrowthTier.fromScrapCount(4)).isEqualTo(GrowthTier.ISLET);
        assertThat(GrowthTier.fromScrapCount(10)).isEqualTo(GrowthTier.ISLET);
        assertThat(GrowthTier.fromScrapCount(11)).isEqualTo(GrowthTier.VILLAGE);
        assertThat(GrowthTier.fromScrapCount(30)).isEqualTo(GrowthTier.VILLAGE);
        assertThat(GrowthTier.fromScrapCount(31)).isEqualTo(GrowthTier.CITY);
        assertThat(GrowthTier.fromScrapCount(1000)).isEqualTo(GrowthTier.CITY);
    }
}
