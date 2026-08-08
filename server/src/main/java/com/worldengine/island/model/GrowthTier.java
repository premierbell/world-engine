package com.worldengine.island.model;

/**
 * Island의 성장 단계 - Growth Point(현재는 scrapCount를 그대로 재사용)를
 * 사람이 체감할 수 있는 이름으로 매핑한다("성장은 체감 가능해야 한다",
 * docs/vision.md 제품 원칙 4번). 경계값은 첫 실사용 데이터 분포를 보고
 * 잡은 가안 - 실사용 근거가 더 쌓이면 조정한다. Growth Point 자체(scrapCount)를
 * 다시 설계할 필요는 없도록 매핑 함수만 여기 둔다.
 */
public enum GrowthTier {
    SEED,
    ISLET,
    VILLAGE,
    CITY;

    public static GrowthTier fromScrapCount(long scrapCount) {
        if (scrapCount <= 3) {
            return SEED;
        }
        if (scrapCount <= 10) {
            return ISLET;
        }
        if (scrapCount <= 30) {
            return VILLAGE;
        }
        return CITY;
    }
}