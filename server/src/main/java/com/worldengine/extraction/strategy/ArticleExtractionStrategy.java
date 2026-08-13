package com.worldengine.extraction.strategy;

import com.worldengine.extraction.model.ExtractionResult;
import com.worldengine.extraction.model.ExtractionStatus;
import com.worldengine.extraction.model.FailureReason;
import com.worldengine.extraction.model.SourceType;
import com.worldengine.extraction.service.ExtractionQualityEvaluator;
import lombok.extern.slf4j.Slf4j;
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
 *
 * jsoup 결과가 법적/정책 boilerplate로 의심되면(사이트 공통 요소만 정적
 * 서빙되고 실제 콘텐츠는 JS로 주입되는 유형, docs/content_extraction.md
 * "Extraction Failure Taxonomy" 참고) PlaywrightExtractionStrategy로
 * 재추출을 시도한다 - 모든 요청에 브라우저를 띄우면 비용이 크므로,
 * 의심될 때만 도는 폴백으로 둔다.
 */
@Slf4j
@Order(Ordered.LOWEST_PRECEDENCE)
@Component
public class ArticleExtractionStrategy implements ExtractionStrategy {

    private static final String USER_AGENT =
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            + "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";
    private static final int TIMEOUT_MS = 10_000;

    private final ExtractionQualityEvaluator extractionQualityEvaluator;
    private final PlaywrightExtractionStrategy playwrightExtractionStrategy;

    public ArticleExtractionStrategy(
        ExtractionQualityEvaluator extractionQualityEvaluator,
        PlaywrightExtractionStrategy playwrightExtractionStrategy) {
        this.extractionQualityEvaluator = extractionQualityEvaluator;
        this.playwrightExtractionStrategy = playwrightExtractionStrategy;
    }

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
        } catch (IllegalArgumentException e) {
            return ExtractionResult.failed(SourceType.ARTICLE, FailureReason.UNSUPPORTED_SOURCE);
        } catch (IOException e) {
            return ExtractionResult.failed(SourceType.ARTICLE, FailureReason.NETWORK_ERROR);
        }

        String content = extractMainContent(uri, document);

        if (extractionQualityEvaluator.looksLikeLegalBoilerplate(content)) {
            log.info("Playwright fallback triggered - url={}, reason=boilerplate_keyword", uri);
            ExtractionResult renderedResult = playwrightExtractionStrategy.extract(uri);
            if (renderedResult.status() == ExtractionStatus.SUCCESS) {
                return renderedResult;
            }
            log.info("Playwright fallback failed, continuing with jsoup result - url={}", uri);
        }

        if (extractionQualityEvaluator.isValid(content)) {
            String title = extractTitle(document);
            String fullPageText = document.body() != null ? document.body().text() : document.text();
            return ExtractionResult.success(title, content.trim(), SourceType.ARTICLE, fullPageText);
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
        String ogTitle = document.select("meta[property=og:title]").attr("content");
        return !ogTitle.isBlank() ? ogTitle : document.title();
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
