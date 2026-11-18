package com.worldengine.scrap.model;

/**
 * 스크랩 생성 중 OpenAI 장애로 끝내지 못한 AI 단계. Scrap.pendingAiStep이 null이면 대기 없음
 * (기존 스크랩은 전부 null이라 마이그레이션 불필요).
 */
public enum PendingAiStep {
    /** 요약(또는 임베딩) 실패 - 본문만 저장됨. resummarize로 복구 */
    SUMMARY,
    /** 추천 판정 실패 - 요약·임베딩까지 저장됨. refreshRecommendations로 복구 */
    RECOMMENDATION
}
