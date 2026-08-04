package com.worldengine.island.service;

import com.worldengine.island.entity.Island;
import org.springframework.stereotype.Service;

/**
 * Island 좌표를 제공하는 단일 진입점 - MapView/줌 카메라/미니맵 등
 * 좌표가 필요한 모든 곳은 이 서비스(또는 이 서비스가 채운 API 응답)만
 * 거친다. DB에 좌표가 있으면 그대로 반환하고, 없으면 임시 좌표(원형
 * 배치)를 계산해서 반환한다 - 임시 값은 저장하지 않는다. Nearest
 * Neighbor 배치가 준비되면 그때 NULL인 Island 전체를 한 번만 계산해서
 * 영구 저장한다. docs/map_home_redesign.md 참고.
 */
@Service
public class MapCoordinateService {

    private static final double PLACEMENT_RADIUS = 220;

    public Coordinate getCoordinate(Island island, int index, int totalCount) {
        if (island.getX() != null && island.getY() != null) {
            return new Coordinate(island.getX(), island.getY());
        }
        return temporaryCircularPlacement(index, totalCount);
    }

    private Coordinate temporaryCircularPlacement(int index, int totalCount) {
        double angle = (2 * Math.PI * index) / totalCount;
        double x = PLACEMENT_RADIUS * Math.cos(angle);
        double y = PLACEMENT_RADIUS * Math.sin(angle);
        return new Coordinate(x, y);
    }

    public record Coordinate(double x, double y) {}
}