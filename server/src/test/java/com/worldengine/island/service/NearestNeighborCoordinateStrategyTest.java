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

    // ===== 2026-11-18 보정(V2): 유사도 분포 기준 거리 + 다음으로 비슷한 섬 쪽 방향 =====

    private static float[] unitAt(double degrees) {
        double radians = Math.toRadians(degrees);
        return new float[]{(float) Math.cos(radians), (float) Math.sin(radians)};
    }

    @Test
    void 옛_상수였다면_둘_다_최대_거리였을_낮은_유사도에서도_더_비슷한_쪽이_더_가깝다() {
        // 놓인 섬끼리 유사도: cos70 = 0.34, cos70 = 0.34, cos140 = -0.77 (실제처럼 0.75보다 한참 낮은 분포)
        List<PlacedIsland> placed = List.of(
            new PlacedIsland(0, 0, unitAt(0)),
            new PlacedIsland(5000, 0, unitAt(70)),
            new PlacedIsland(0, 5000, unitAt(140)));

        // 둘 다 가장 비슷한 섬은 (0,0)이고 유사도는 0.75 미만(0.30, 0.00) - 예전 상수로는 둘 다 450
        MapCoordinateService.Coordinate closer = strategy.calculate(unitAt(-72.5), placed);
        MapCoordinateService.Coordinate farther = strategy.calculate(unitAt(-90), placed);

        double closerDistance = Math.hypot(closer.x(), closer.y());
        double fartherDistance = Math.hypot(farther.x(), farther.y());
        assertThat(closerDistance).isLessThan(fartherDistance);
        assertThat(fartherDistance).isLessThan(450);
    }

    @Test
    void 다음으로_비슷한_섬_쪽에_놓인다() {
        PlacedIsland anchor = new PlacedIsland(0, 0, unitAt(0));
        PlacedIsland secondMostSimilar = new PlacedIsland(1000, 0, unitAt(50));
        PlacedIsland dissimilar = new PlacedIsland(-1000, 0, unitAt(180));

        // 새 섬: anchor와 cos20 = 0.94, 두 번째 섬과 cos30 = 0.87, 반대쪽 섬과는 음수
        MapCoordinateService.Coordinate result = strategy.calculate(unitAt(20), List.of(anchor, secondMostSimilar, dissimilar));

        assertThat(result.x()).isPositive();
        assertThat(Math.abs(result.y())).isLessThan(1e-6);
    }
}
