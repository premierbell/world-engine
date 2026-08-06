package com.worldengine.island.service;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class NearestNeighborCoordinateStrategyTest {

    private final NearestNeighborCoordinateStrategy strategy = new NearestNeighborCoordinateStrategy();

    @Test
    void placesFirstIslandAtOrigin() {
        MapCoordinateService.Coordinate result = strategy.calculate(new float[]{1f, 0f}, List.of());

        assertThat(result.x()).isZero();
        assertThat(result.y()).isZero();
    }

    @Test
    void picksMostSimilarIslandAsAnchor() {
        PlacedIsland similar = new PlacedIsland(1000, 1000, new float[]{1f, 0f});
        PlacedIsland different = new PlacedIsland(-1000, -1000, new float[]{0f, 1f});

        MapCoordinateService.Coordinate result = strategy.calculate(new float[]{1f, 0f}, List.of(similar, different));

        double distanceFromSimilar = Math.hypot(result.x() - 1000, result.y() - 1000);
        double distanceFromDifferent = Math.hypot(result.x() - (-1000), result.y() - (-1000));
        assertThat(distanceFromSimilar).isLessThan(distanceFromDifferent);
    }

    @Test
    void higherSimilarityProducesSmallerRadius() {
        PlacedIsland anchor = new PlacedIsland(0, 0, new float[]{1f, 0f});

        MapCoordinateService.Coordinate closeResult = strategy.calculate(new float[]{1f, 0f}, List.of(anchor));
        MapCoordinateService.Coordinate farResult = strategy.calculate(new float[]{0f, 1f}, List.of(anchor));

        double closeDistance = Math.hypot(closeResult.x(), closeResult.y());
        double farDistance = Math.hypot(farResult.x(), farResult.y());
        assertThat(closeDistance).isLessThan(farDistance);
    }

    @Test
    void expandsRadiusWhenFirstRingIsBlocked() {
        PlacedIsland anchor = new PlacedIsland(0, 0, new float[]{1f, 0f});
        List<PlacedIsland> placed = new ArrayList<>();
        placed.add(anchor);

        double firstRingRadius = 120; // similarity=1.0일 때 목표 반경(MIN_DISTANCE)
        for (int i = 0; i < 8; i++) {
            double angle = (2 * Math.PI * i) / 8;
            double x = firstRingRadius * Math.cos(angle);
            double y = firstRingRadius * Math.sin(angle);
            placed.add(new PlacedIsland(x, y, new float[]{0f, 1f})); // 유사도 낮게 둬서 anchor로 안 뽑히게
        }

        MapCoordinateService.Coordinate result = strategy.calculate(new float[]{1f, 0f}, placed);

        double distanceFromAnchor = Math.hypot(result.x(), result.y());
        assertThat(distanceFromAnchor).isGreaterThan(firstRingRadius);
    }
}
