package com.worldengine.extraction.strategy;

import com.microsoft.playwright.Browser;
import com.microsoft.playwright.BrowserType;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Playwright;
import com.microsoft.playwright.PlaywrightException;
import com.microsoft.playwright.TimeoutError;
import com.microsoft.playwright.options.WaitUntilState;
import com.worldengine.extraction.model.ExtractionResult;
import com.worldengine.extraction.model.FailureReason;
import com.worldengine.extraction.model.SourceType;
import com.worldengine.extraction.service.ExtractionQualityEvaluator;
import java.net.URI;
import lombok.extern.slf4j.Slf4j;
import net.dankito.readability4j.Article;
import net.dankito.readability4j.Readability4J;
import net.dankito.readability4j.extended.Readability4JExtended;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.springframework.stereotype.Component;

/**
 * ArticleExtractionStrategy가 정적 HTML(jsoup)만으로 boilerplate를
 * 의심할 때 호출하는 재추출 경로 - 실제 브라우저(Chromium)로 페이지를
 * 열어 JS 렌더링이 끝난 뒤의 HTML을 가져온다. 라우팅 체인(supports())에는
 * 절대 직접 등록되지 않는다 - ArticleExtractionStrategy가 명시적으로
 * 호출할 때만 쓰인다. docs/content_extraction.md의 "Extraction Failure
 * Taxonomy" 참고.
 */
@Slf4j
@Component
public class PlaywrightExtractionStrategy implements ExtractionStrategy {

    private static final int TIMEOUT_MS = 15_000;

    private final ExtractionQualityEvaluator extractionQualityEvaluator;

    public PlaywrightExtractionStrategy(ExtractionQualityEvaluator extractionQualityEvaluator) {
        this.extractionQualityEvaluator = extractionQualityEvaluator;
    }

    @Override
    public boolean supports(URI uri) {
        return false;
    }

    @Override
    public ExtractionResult extract(URI uri) {
        String renderedHtml;
        try (Playwright playwright = Playwright.create()) {
            try (Browser browser = playwright.chromium().launch(
                new BrowserType.LaunchOptions().setHeadless(true))) {
                try (Page page = browser.newPage()) {
                    page.navigate(uri.toString(), new Page.NavigateOptions()
                        .setTimeout(TIMEOUT_MS)
                        .setWaitUntil(WaitUntilState.NETWORKIDLE));
                    renderedHtml = page.content();
                }
            }
        } catch (TimeoutError e) {
            return ExtractionResult.failed(SourceType.ARTICLE, FailureReason.TIMEOUT);
        } catch (PlaywrightException e) {
            return ExtractionResult.failed(SourceType.ARTICLE, FailureReason.NETWORK_ERROR);
        }

        Document document = Jsoup.parse(renderedHtml, uri.toString());
        String content = extractMainContent(uri, document);

        if (extractionQualityEvaluator.looksLikeLegalBoilerplate(content)) {
            log.warn("Playwright rendered successfully but readability4j still picked boilerplate - "
                + "url={}, contentLength={}", uri, content == null ? 0 : content.length());
        }

        if (extractionQualityEvaluator.isValid(content)) {
            return ExtractionResult.success(document.title(), content.trim(), SourceType.ARTICLE);
        }
        return ExtractionResult.failed(SourceType.ARTICLE, FailureReason.EMPTY_CONTENT);
    }

    private String extractMainContent(URI uri, Document document) {
        try {
            Readability4J readability4J = new Readability4JExtended(uri.toString(), document.outerHtml());
            Article article = readability4J.parse();
            return article.getTextContent();
        } catch (Exception e) {
            return null;
        }
    }

}
