package com.worldengine.extraction.strategy;

import com.worldengine.extraction.model.ExtractionResult;

import java.net.URI;

/**
 * 소스 유형별 추출 전략 인터페이스. ContentExtractionService가 URI를
 * 보고 supports()가 true인 전략을 찾아 extract()를 위임한다 -
 * NaverBlogExtractionStrategy, GithubExtractionStrategy 등을 이
 * 인터페이스로 추가하면 된다. docs/content_extraction.md 참고.
 */
public interface ExtractionStrategy {

    boolean supports(URI uri);

    ExtractionResult extract(URI uri);
}
