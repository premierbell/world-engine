package com.worldengine.scrap.repository;

/**
 * 섬 멤버 중 추천/섬 벡터 계산에 필요한 것만 담는 조회 전용 결과.
 * 엔티티 전체(본문 약 7.6KB 포함)를 읽으면 1만 건/가장 큰 섬 약 4,000건 기준 1,515ms였고,
 * 그중 본문 전송 23% + JPA 엔티티 생성 부담 약 40%(추정)는 이 계산에 필요 없다
 * (experiments/v0_validation.md, 2026-11-18 멤버 읽기 비용 분리 측정).
 */
public record IslandMemberVector(Long id, String summary, float[] embedding) {
}
