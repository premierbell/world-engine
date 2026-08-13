package com.worldengine.extraction.strategy;

import com.worldengine.extraction.model.ExtractionResult;
import com.worldengine.extraction.model.FailureReason;
import com.worldengine.extraction.model.SourceType;
import java.io.IOException;
import java.net.SocketTimeoutException;
import java.net.URI;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.jsoup.HttpStatusException;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/**
 * 네이버 블로그 전용 전략 - 겉으로 보이는 URL(blog.naver.com/{blogId}/{logNo})은
 * iframe(mainFrame) 래퍼고, 실제 본문은 PostView.naver?blogId=...&logNo=...
 * 페이지 안 div.se-main-container에 있다. URL 경로에서 blogId/logNo를
 * 직접 파싱해서 iframe 요청 없이 바로 PostView 페이지를 가져온다.
 * docs/content_extraction.md 참고.
 */

@Order(1)
@Component
public class NaverBlogExtractionStrategy implements ExtractionStrategy {

    private static final String USER_AGENT =
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            + "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";
    private static final int TIMEOUT_MS = 10_000;
    private static final Pattern BLOG_ID_LOG_NO_PATTERN = Pattern.compile("^/([^/]+)/(\\d+)$");

    @Override
    public boolean supports(URI uri) {
        String host = uri.getHost();
        return host != null && host.endsWith("blog.naver.com");
    }

    @Override
    public ExtractionResult extract(URI uri) {
        String postViewUrl = toPostViewUrl(uri);
        if (postViewUrl == null) {
            return ExtractionResult.failed(SourceType.NAVER_BLOG, FailureReason.UNSUPPORTED_SOURCE);
        }

        Document document;
        try {
            document = Jsoup.connect(postViewUrl)
                .userAgent(USER_AGENT)
                .timeout(TIMEOUT_MS)
                .get();
        } catch (SocketTimeoutException e) {
            return ExtractionResult.failed(SourceType.NAVER_BLOG, FailureReason.TIMEOUT);
        } catch (HttpStatusException e) {
            FailureReason reason = (e.getStatusCode() == 403 || e.getStatusCode() == 401)
                ? FailureReason.ROBOTS_BLOCKED
                : FailureReason.NETWORK_ERROR;
            return ExtractionResult.failed(SourceType.NAVER_BLOG, reason);
        } catch (IOException e) {
            return ExtractionResult.failed(SourceType.NAVER_BLOG, FailureReason.NETWORK_ERROR);
        }

        Element mainContainer = document.selectFirst("div.se-main-container");
        if (mainContainer != null) {
            String content = mainContainer.text();
            if (!content.isBlank()) {
                return ExtractionResult.success(extractTitle(document), content.trim(), SourceType.NAVER_BLOG);
            }
        }

        return openGraphFallback(document);
    }

    /** blog.naver.com/{blogId}/{logNo} 형태에서 PostView.naver URL을 직접 구성한다. */
    private String toPostViewUrl(URI uri) {
        Matcher matcher =  BLOG_ID_LOG_NO_PATTERN.matcher(uri.getPath());
        if (!matcher.matches()) {
            return null;
        }
        String blogId = matcher.group(1);
        String logNo = matcher.group(2);
        return "https://blog.naver.com/PostView.naver?blogId=" + blogId + "&logNo=" + logNo;
    }

    private String extractTitle(Document document) {
        String ogTitle = document.select("meta[property=og:title]").attr("content");
        return !ogTitle.isBlank() ? ogTitle : document.title();
    }

    private ExtractionResult openGraphFallback(Document document) {
        String ogTitle = document.select("meta[property=og:title]").attr("content");
        String ogDescription = document.select("meta[property=og:description]").attr("content");

        if (ogDescription.isBlank()) {
            return ExtractionResult.failed(SourceType.NAVER_BLOG, FailureReason.EMPTY_CONTENT);
        }

        String title = extractTitle(document);
        return ExtractionResult.openGraphOnly(title, ogDescription, SourceType.NAVER_BLOG);
    }
}
