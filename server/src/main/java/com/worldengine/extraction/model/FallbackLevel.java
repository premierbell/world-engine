package com.worldengine.extraction.model;

/**
 * 숫자가 클수록 정보 손실이 크다 - 로그/통계에서 등급으로 취급한다.
 * docs/content_extraction.md 참고.
 */
public enum FallbackLevel {
    DIRECT_EXTRACTION(0),
    OPEN_GRAPH_ONLY(1),
    SEARCH_SNIPPET(2),
    USER_INPUT(3),
    EXTRACTION_FAILED(4);

    private final int level;

    FallbackLevel(int level) {
        this.level = level;
    }

    public int level() {
        return level;
    }
}
