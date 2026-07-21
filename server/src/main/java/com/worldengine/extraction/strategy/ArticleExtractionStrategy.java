package com.worldengine.extraction.strategy;

import com.worldengine.extraction.model.ExtractionResult;
import com.worldengine.extraction.model.FailureReason;
import com.worldengine.extraction.model.SourceType;
import net.dankito.readability4j.Article;
import net.dankito.readability4j.Readability4J;
import net.dankito.readability4j.extended.Readability4JExtended;
import org.jsoup.HttpStatusException;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.net.SocketTimeoutException;
import java.net.URI;

/**
 * 일반 기사/블로그(티스토리, 브런치, Notion 공개 페이지 등 정적 HTML로
 * 서빙되는 소스)에 대한 기본 추출 전략 - jsoup으로 HTML을 가져오고
 * readability4j(Mozilla Readability 알고리즘의 Kotlin/Java 포트)로
 * 본문을 뽑는다. 다른 전략이 처리하지 않는 URI의 기본값(fallback) 역할도
 * 겸한다 - supports()가 항상 true라 반드시 라우팅 체인의 마지막에 둔다.
 * docs/content_extraction.md 참고.
 */

@Order(Ordered.LOWEST_PRECEDENCE)
@Component
public class ArticleExtractionStrategy implements ExtractionStrategy {

    private static final String USER_AGENT =
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            + "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";
    private static final int TIMEOUT_MS = 10_000;

    @Override
    public boolean supports(URI uri) {
        return true;
    }

    @Override
    public ExtractionResult extract(URI uri) {
        Document document;
        try {
            document = Jsoup.connect(uri.toString())
                .userAgent(USER_AGENT)
                .timeout(TIMEOUT_MS)
                .get();
        } catch (SocketTimeoutException e) {
            return ExtractionResult.failed(SourceType.ARTICLE, FailureReason.TIMEOUT);
        } catch (HttpStatusException e) {
            FailureReason reason = (e.getStatusCode() == 403 || e.getStatusCode() == 401)
                ? FailureReason.ROBOTS_BLOCKED
                : FailureReason.NETWORK_ERROR;
            return ExtractionResult.failed(SourceType.ARTICLE, reason);
        } catch (IOException e) {
            return ExtractionResult.failed(SourceType.ARTICLE, FailureReason.NETWORK_ERROR);
        }

        String content = extractMainContent(uri, document);
        if (content != null && !content.isBlank()) {
            String title = extractTitle(document);
            return ExtractionResult.success(title, content.trim(), SourceType.ARTICLE);
        }

        return openGraphFallback(document);
    }

    private String extractMainContent(URI uri, Document document) {
        try {
            Readability4J readability4J = new Readability4JExtended(uri.toString(), document.outerHtml());
            Article article = readability4J.parse();
            return article.getTextContent();
        } catch (Exception e) {
            // readability4j 파싱 자체가 실패하는 경우(구조가 예상과 다른 페이지 등) -
            // 예외를 던지지 않고 Open Graph fallback으로 넘긴다.
            return null;
        }
    }

    private String extractTitle(Document document) {
        return document.title();
    }

    private ExtractionResult openGraphFallback(Document document) {
        String ogTitle = document.select("meta[property=og:title]").attr("content");
        String ogDescription = document.select("meta[property=og:description]").attr("content");

        if (ogDescription.isBlank()) {
            return ExtractionResult.failed(SourceType.ARTICLE, FailureReason.EMPTY_CONTENT);
        }

        String title = !ogTitle.isBlank() ? ogTitle : document.title();
        return ExtractionResult.openGraphOnly(title, ogDescription, SourceType.ARTICLE);
    }
}
