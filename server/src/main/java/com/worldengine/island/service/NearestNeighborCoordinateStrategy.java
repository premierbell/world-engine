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
 */
@Component
public class NearestNeighborCoordinateStrategy {

    // similarity → 목표 반경 매핑 상수. 정확한 값은 실제 렌더러로
    // 확인하며 튜닝할 것(아직 가안).
    private static final double HIGH = 0.95;
    private static final double LOW = 0.75;
    private static final double MIN_DISTANCE = 120;
    private static final double MAX_DISTANCE = 450;
    private static final double CURVE_K = 2;

    // 충돌 회피 - 다른 Island와 이 거리 미만이면 겹친 것으로 본다.
    // MIN_DISTANCE와 같은 값 재사용(가장 비슷한 두 섬이 허용하는
    // 최소 간격과, 물리적으로 허용하는 최소 간격을 같은 개념으로 둠).
    private static final double COLLISION_MARGIN = MIN_DISTANCE;
    private static final int DIRECTION_COUNT = 8;
    private static final double RADIUS_STEP = 60;
    private static final int MAX_RADIUS_EXPANSIONS = 20;

    public MapCoordinateService.Coordinate calculate(float[] embedding, List<PlacedIsland> placed) {
        if (placed.isEmpty()) {
            return new MapCoordinateService.Coordinate(0, 0);
        }

        PlacedIsland anchor = findAnchor(embedding, placed);
        double similarity = CosineSimilarity.similarity(embedding, anchor.embedding());
        double baseRadius = radiusFromSimilarity(similarity);

        return findOpenSpot(anchor, baseRadius, placed);
    }

    private PlacedIsland findAnchor(float[] embedding, List<PlacedIsland> placed) {
        return placed.stream()
            .max((a, b) -> Double.compare(
                CosineSimilarity.similarity(embedding, a.embedding()),
                CosineSimilarity.similarity(embedding, b.embedding())))
            .orElseThrow();
    }

    private double radiusFromSimilarity(double similarity) {
        double normalized = clamp((HIGH - similarity) / (HIGH - LOW), 0, 1);
        return MIN_DISTANCE + (MAX_DISTANCE - MIN_DISTANCE) * Math.pow(normalized, CURVE_K);
    }

    private MapCoordinateService.Coordinate findOpenSpot(PlacedIsland anchor, double baseRadius, List<PlacedIsland> placed) {
        double startAngle = startAngleFromAnchor(anchor);
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
            if (Math.sqrt(dx * dx + dy * dy) < COLLISION_MARGIN) {
                return false;
            }
        }
        return true;
    }

    private double clamp(double value, double min, double max) {
        return Math.max(min, Math.min(max, value));
    }
}
