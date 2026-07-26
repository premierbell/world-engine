package com.worldengine.extraction.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * 추출된 content가 "실제 본문"이라 부를 만큼 충분한지 판단한다 -
 * 빈 문자열만 걸러내던 기존 체크(isBlank)로는 SPA 랜딩페이지처럼
 * 제목만 있는 껍데기 HTML도 "성공"으로 오판했다(실사용 중 발견).
 */
@Component
public class ExtractionQualityEvaluator {

    private final int minContentLength;

    public ExtractionQualityEvaluator(@Value("${extraction.min-content-length}") int minContentLength) {
        this.minContentLength = minContentLength;
    }

    public boolean isValid(String content) {
        return content != null && content.trim().length() >= minContentLength;
    }
}
