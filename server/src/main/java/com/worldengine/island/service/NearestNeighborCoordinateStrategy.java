package com.worldengine.island.service;

import com.worldengine.recommendation.vector.CosineSimilarity;
import java.util.Arrays;
import java.util.List;
import org.springframework.stereotype.Component;

/**
 * 새 Island의 좌표를 "가장 비슷한 기존 Island(anchor) 옆, 안 겹치는
 * 자리"로 계산한다 - 임베딩을 2차원으로 압축하는 게 아니라 고차원
 * 그대로 비교하고 결과만 2차원 배치에 쓴다. 방향은 anchor가, 거리는
 * similarity가, 실제 빈자리는 충돌 회피가 정한다.
 * docs/map_home_redesign.md "Nearest Neighbor 배치 알고리즘" 참고.
 * 거리 기준은 이미 놓인 섬들의 유사도 분포로 보정하고, 방향은 다음으로 비슷한 섬들 쪽을 먼저 본다
 * (2026-11-18 측정·시뮬레이션, experiments/v0_validation.md). 새 섬에만 적용 - 기존 섬 좌표는 그대로.
 */
@Component
public class NearestNeighborCoordinateStrategy {

    // similarity → 목표 반경 매핑.
    // 처음 상수(HIGH 0.95 / LOW 0.75)는 가안이었는데, 실측해 보니 실제 섬끼리 유사도는 0.13~0.42라
    // 9번 배치가 모두 최대 거리(450)였다 - "얼마나 비슷한가"가 지도에 반영되지 않음
    // (experiments/v0_validation.md 2026-11-18). 그래서 이미 놓인 섬끼리 유사도의 90/10백분위를
    // HIGH/LOW로 쓴다(상대 보정). 놓인 섬이 3개 미만이면 분포를 알 수 없어 고정값을 쓴다.
    private static final double FALLBACK_HIGH = 0.95;
    private static final double FALLBACK_LOW = 0.75;
    private static final int MIN_ISLANDS_FOR_RELATIVE_RANGE = 3;
    private static final double HIGH_PERCENTILE = 90;
    private static final double LOW_PERCENTILE = 10;
    private static final double MIN_DISTANCE = 120;
    private static final double MAX_DISTANCE = 450;
    private static final double CURVE_K = 2;

    // 충돌 회피 - 다른 Island와 이 거리 미만이면 겹친 것으로 본다.
    // MIN_DISTANCE와 같은 값 재사용(가장 비슷한 두 섬이 허용하는
    // 최소 간격과, 물리적으로 허용하는 최소 간격을 같은 개념으로 둠).
    private static final double COLLISION_MARGIN = MIN_DISTANCE;
    // 최소 반경(120)으로 놓으면 후보와 anchor 거리가 정확히 120이라, 반올림 오차로 같은 자리가
    // 빈자리/막힘으로 갈렸다(시뮬레이션 대조에서 발견) - 경계에 딱 걸린 자리는 빈자리로 본다.
    private static final double COLLISION_EPSILON = 1e-6;
    private static final int DIRECTION_COUNT = 8;
    private static final double RADIUS_STEP = 60;
    private static final int MAX_RADIUS_EXPANSIONS = 20;

    public MapCoordinateService.Coordinate calculate(float[] embedding, List<PlacedIsland> placed) {
        if (placed.isEmpty()) {
            return new MapCoordinateService.Coordinate(0, 0);
        }

        double[] similarities = placed.stream()
            .mapToDouble(island -> CosineSimilarity.similarity(embedding, island.embedding()))
            .toArray();
        int anchorIndex = indexOfMax(similarities);
        PlacedIsland anchor = placed.get(anchorIndex);

        double baseRadius = radiusFromSimilarity(similarities[anchorIndex], similarityRange(placed));
        double startAngle = startAngle(anchorIndex, similarities, placed);

        return findOpenSpot(anchor, baseRadius, startAngle, placed);
    }

    private int indexOfMax(double[] values) {
        int best = 0;
        for (int i = 1; i < values.length; i++) {
            if (values[i] > values[best]) {
                best = i;
            }
        }
        return best;
    }

    private SimilarityRange similarityRange(List<PlacedIsland> placed) {
        SimilarityRange fallback = new SimilarityRange(FALLBACK_HIGH, FALLBACK_LOW);
        if (placed.size() < MIN_ISLANDS_FOR_RELATIVE_RANGE) {
            return fallback;
        }
        int n = placed.size();
        double[] pairs = new double[n * (n - 1) / 2];
        int k = 0;
        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                pairs[k++] = CosineSimilarity.similarity(placed.get(i).embedding(), placed.get(j).embedding());
            }
        }
        Arrays.sort(pairs);
        double high = percentile(pairs, HIGH_PERCENTILE);
        double low = percentile(pairs, LOW_PERCENTILE);
        return high > low ? new SimilarityRange(high, low) : fallback;
    }

    // 선형 보간 백분위 - 시뮬레이션(numpy.percentile 기본값)과 같은 방식
    private double percentile(double[] sorted, double percent) {
        double position = percent / 100 * (sorted.length - 1);
        int lower = (int) Math.floor(position);
        int upper = (int) Math.ceil(position);
        return sorted[lower] + (sorted[upper] - sorted[lower]) * (position - lower);
    }

    private double radiusFromSimilarity(double similarity, SimilarityRange range) {
        double normalized = clamp((range.high() - similarity) / (range.high() - range.low()), 0, 1);
        return MIN_DISTANCE + (MAX_DISTANCE - MIN_DISTANCE) * Math.pow(normalized, CURVE_K);
    }

    private MapCoordinateService.Coordinate findOpenSpot(PlacedIsland anchor, double baseRadius, double startAngle, List<PlacedIsland> placed) {
        double radius = baseRadius;
        for (int expansion = 0; expansion < MAX_RADIUS_EXPANSIONS; expansion++) {
            for (int i = 0; i < DIRECTION_COUNT; i++) {
                double angle = startAngle + (2 * Math.PI * i) / DIRECTION_COUNT;
                double x = anchor.x() + radius * Math.cos(angle);
                double y = anchor.y() + radius * Math.sin(angle);
                if (noCollision(x, y, placed)) {
                    return new MapCoordinateService.Coordinate(x, y);
                }
            }
            radius += RADIUS_STEP;
        }
        // 안전장치 - 여기까지 오면 사실상 비정상 상황(섬이 극단적으로 많이 몰림)
        return new MapCoordinateService.Coordinate(anchor.x() + radius, anchor.y());
    }

    // 빈자리를 "anchor 다음으로 비슷한 섬들(유사도 가중 평균 위치)" 쪽부터 찾는다. 거리만 보정하면
    // anchor 말고 다른 섬과의 거리는 방향(해시)에 맡겨져 의미가 거의 반영되지 않았다(시뮬레이션 V1 → V2).
    // 그런 섬이 없으면(anchor뿐이거나 나머지 유사도가 0 이하) 기존처럼 anchor 해시 각도를 쓴다.
    private double startAngle(int anchorIndex, double[] similarities, List<PlacedIsland> placed) {
        PlacedIsland anchor = placed.get(anchorIndex);
        double weightSum = 0;
        double targetX = 0;
        double targetY = 0;
        for (int i = 0; i < placed.size(); i++) {
            if (i == anchorIndex || similarities[i] <= 0) {
                continue;
            }
            weightSum += similarities[i];
            targetX += similarities[i] * placed.get(i).x();
            targetY += similarities[i] * placed.get(i).y();
        }
        if (weightSum == 0) {
            return startAngleFromAnchor(anchor);
        }
        double dx = targetX / weightSum - anchor.x();
        double dy = targetY / weightSum - anchor.y();
        if (Math.hypot(dx, dy) < 1e-9) {
            return startAngleFromAnchor(anchor);
        }
        return Math.atan2(dy, dx);
    }

    // 탐색 시작 각도를 anchor의 임베딩에서 결정론적으로 뽑는다. 이게 없으면
    // 모든 섬이 항상 각도 0(오른쪽)부터 탐색을 시작해서, anchor가 바뀌어도
    // 매번 같은 절대 방향으로 뻗어나가며 일직선으로 늘어서는 편향이 생긴다
    // ("철도 선로" 패턴, 실제 렌더링에서 관찰됨). anchor마다 다른 시작 각도를
    // 쓰면 같은 입력(같은 anchor)엔 항상 같은 결과가 나오면서도(재현 가능),
    // 서로 다른 anchor를 타는 섬들은 서로 다른 방향으로 퍼진다.
    private double startAngleFromAnchor(PlacedIsland anchor) {
        int hash = Arrays.hashCode(anchor.embedding());
        int degrees = Math.floorMod(hash, 360);
        return Math.toRadians(degrees);
    }

    private boolean noCollision(double x, double y, List<PlacedIsland> placed) {
        for (PlacedIsland island : placed) {
            double dx = x - island.x();
            double dy = y - island.y();
            if (Math.sqrt(dx * dx + dy * dy) < COLLISION_MARGIN - COLLISION_EPSILON) {
                return false;
            }
        }
        return true;
    }

    private double clamp(double value, double min, double max) {
        return Math.max(min, Math.min(max, value));
    }

    private record SimilarityRange(double high, double low) {}
}
