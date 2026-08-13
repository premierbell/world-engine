package com.worldengine.recommendation.client;

import org.springframework.stereotype.Component;

/**
 * 추출된 원문을 그냥 잘라서 저장하던 것(ScrapContentPreprocessor.truncate()
 * 결과를 그대로 summary로 썼음)을 대체 - "요약"이라는 필드명과 달리 실제로는
 * AI 요약이 아니었던 걸 실사용 중 발견해서 수정. 저작권/약관/편집제한 안내
 * 같은 사이트 운영 정책 문구는 요약에서 제외하도록 프롬프트에 명시 - 나무위키
 * 저작권/IP안내 혼입 사례(라이브 테스트로 실제 검증: 혼합 케이스에서 정책
 * 문구 제외하고 실제 내용만 추출됨, 순수 정책 문구만 있으면 NO_CONTENT 정확히
 * 반환됨) 대응.
 *
 * summarize()가 NO_CONTENT를 반환하면(readability4j가 고른 좁은 범위가
 * boilerplate뿐이었다는 뜻) ScrapService가 summarizeFullPage()로 페이지
 * 전체 텍스트를 한 번 더 보여주고 "네가 직접 찾아봐"라고 시키는 2차 폴백을
 * 시도한다 - readability4j를 버리는 게 아니라, readability4j가 놓친
 * 경우에만 더 넓게 다시 보는 구조(KT위즈샵 상품 페이지 실사례로 검증:
 * readability4j는 반품정책만 골랐지만 전체 텍스트를 주면 상품명/가격/
 * 사이즈를 정확히 찾아냄).
 */
@Component
public class ContentSummaryClient {

    public static final String NO_CONTENT = "NO_CONTENT";

    private static final String PROMPT = """
        다음은 웹페이지에서 추출한 원문이다. 이 페이지 고유의 주제(예: 특정
        장소, 인물, 개념, 사건 등)에 대한 실질적인 정보만 3~5문장으로
        요약하라.

        저작권 고지, 이용약관, 쿠키 안내, 편집 제한 안내, 반품/배송 정책
        같은 사이트 운영 정책 문구는 절대 요약 대상이 아니다 - 이런 문구를
        발견하면 무시하고, 그 정책 문구 자체를 설명하거나 요약하지 마라.

        원문 전체가 이런 운영 정책 문구뿐이고 페이지 고유 주제에 대한 정보가
        전혀 없다면, 다른 말 없이 "NO_CONTENT"라고만 출력하라.

        원문: %s
        """;

    private static final String FULL_PAGE_PROMPT = """
        다음은 웹페이지 전체에서 태그를 제거하고 남은 텍스트다. 메뉴,
        네비게이션, 검색창, 장바구니 버튼 같은 UI 텍스트와 배송·교환·반품·
        약관 같은 사이트 운영 정책 문구가 섞여 있을 수 있으니 무시하라.

        그중 이 페이지가 실제로 다루는 대상(상품/기사/장소 등)에 대한 핵심
        정보만 스스로 찾아 3~5문장으로 요약하라. 상품 페이지라면 상품명,
        가격, 주요 옵션(사이즈 등) 정보를 반드시 포함하라.

        의미 있는 본문을 찾을 수 없다면, 다른 말 없이 "NO_CONTENT"라고만
        출력하라.

        원문: %s
        """;

    private final OpenAiChatClient chatClient;

    public ContentSummaryClient(OpenAiChatClient chatClient) {
        this.chatClient = chatClient;
    }

    public String summarize(String content) {
        return chatClient.complete(PROMPT.formatted(content));
    }

    public String summarizeFullPage(String fullPageText) {
        return chatClient.complete(FULL_PAGE_PROMPT.formatted(fullPageText));
    }
}
