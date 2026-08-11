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

    /**
     * 본문 대신 사이트 공통 요소(주소/사업자정보/저작권/약관 안내)만
     * 잡힌 경우를 감지한다 - 실사용 중 발견(docs/content_extraction.md
     * "Extraction Failure Taxonomy" 참고). 이커머스 어휘와 달리 이런
     * 문구는 페이지당 한 번씩만 등장하는 경향이 있어(링크 텍스트) threshold를
     * 1로 둔다. "쿠키"를 단독 키워드로 넣었더니 "세쿠키누맙" 같은
     * 무관한 단어의 부분 문자열에 매치되는 오탐이 나와서 "쿠키를"/"쿠키
     * 수집"처럼 구체적인 구문만 쓴다.
     */
    private static final List<String> LEGAL_BOILERPLATE_KEYWORDS = List.of(
        "개인정보처리방침", "약관", "저작권", "All rights reserved", "사업자등록번호",
        "통신판매업", "통신판매중개자", "Copyright", "쿠키를", "쿠키 수집", "개인정보 처리방침"
    );
    private static final int LEGAL_KEYWORD_THRESHOLD = 1;
    private static final int LEGAL_CHECK_WINDOW = 500;

    private final int minContentLength;

    public ExtractionQualityEvaluator(@Value("${extraction.min-content-length}") int minContentLength) {
        this.minContentLength = minContentLength;
    }

    public boolean isValid(String content) {
        if (content == null || content.trim().length() < minContentLength) {
            return false;
        }
        return !looksLikeCommerceBoilerplate(content) && !looksLikeLegalBoilerplate(content);
    }

    public boolean looksLikeLegalBoilerplate(String content) {
        if (content == null) {
            return false;
        }
        String window = content.length() > LEGAL_CHECK_WINDOW
            ? content.substring(0, LEGAL_CHECK_WINDOW)
            : content;
        long matchCount = LEGAL_BOILERPLATE_KEYWORDS.stream().filter(window::contains).count();
        return matchCount >= LEGAL_KEYWORD_THRESHOLD;
    }

    private boolean looksLikeCommerceBoilerplate(String content) {
        String window = content.length() > COMMERCE_CHECK_WINDOW
            ? content.substring(0, COMMERCE_CHECK_WINDOW)
            : content;
        long matchCount = COMMERCE_OPERATIONAL_KEYWORDS.stream().filter(window::contains).count();
        return matchCount >= COMMERCE_KEYWORD_THRESHOLD;
    }
}
