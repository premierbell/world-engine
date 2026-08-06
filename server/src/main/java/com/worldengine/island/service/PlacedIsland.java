package com.worldengine.island.service;

/**
 * NearestNeighborCoordinateStrategy가 비교 대상으로 쓰는 "이미 좌표가
 * 확정된 Island"의 순수 튜플 - JPA 엔티티에 안 묶여서 신규 생성/
 * 마이그레이션 양쪽에서 재사용 가능. x,y가 NULL인(아직 임시 좌표인)
 * Island는 여기 들어가면 안 됨 - docs/map_home_redesign.md 참고.
 */
public record PlacedIsland(double x, double y, float[] embedding) {}
