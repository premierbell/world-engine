package com.worldengine.extraction.service;

import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * 추출된 content가 "실제 본문"이라 부를 만큼 충분한지 판단한다 -
 * 빈 문자열만 걸러내던 기존 체크(isBlank)로는 SPA 랜딩페이지처럼
 * 제목만 있는 껍데기 HTML도 "성공"으로 오판했다(실사용 중 발견).
 *
 * 길이가 충분해도 실제로는 이커머스 페이지의 배송/교환/반품 안내
 * 같은 운영 문구를 본문으로 잘못 집어온 경우가 있어(실사용 중 서로
 * 다른 쇼핑몰 2곳에서 독립적으로 확인), 운영 어휘 밀도도 함께 본다.
 */
@Component
public class ExtractionQualityEvaluator {

    private static final List<String> COMMERCE_OPERATIONAL_KEYWORDS = List.of(
        "배송", "교환", "반품", "환불", "쿠폰", "적립", "상품번호", "모델번호", "결제", "무료배송", "택배"
    );
    private static final int COMMERCE_KEYWORD_THRESHOLD = 3;
    private static final int COMMERCE_CHECK_WINDOW = 500;

    private final int minContentLength;

    public ExtractionQualityEvaluator(@Value("${extraction.min-content-length}") int minContentLength) {
        this.minContentLength = minContentLength;
    }

    public boolean isValid(String content) {
        if (content == null || content.trim().length() < minContentLength) {
            return false;
        }
        return !looksLikeCommerceBoilerplate(content);
    }

    private boolean looksLikeCommerceBoilerplate(String content) {
        String window = content.length() > COMMERCE_CHECK_WINDOW
            ? content.substring(0, COMMERCE_CHECK_WINDOW)
            : content;
        long matchCount = COMMERCE_OPERATIONAL_KEYWORDS.stream().filter(window::contains).count();
        return matchCount >= COMMERCE_KEYWORD_THRESHOLD;
    }
}
