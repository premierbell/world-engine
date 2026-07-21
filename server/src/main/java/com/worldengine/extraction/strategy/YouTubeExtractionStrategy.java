package com.worldengine.extraction.strategy;

import com.worldengine.extraction.model.ExtractionResult;
import com.worldengine.extraction.model.FailureReason;
import com.worldengine.extraction.model.SourceType;
import java.io.IOException;
import java.net.SocketTimeoutException;
import java.net.URI;
import org.jsoup.HttpStatusException;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/**
 * YouTube 영상 - Data API(키 필요) 대신 watch 페이지 HTML의
 * og:title/og:description(영상 설명)을 추출한다. 자막은 다루지 않는다
 * (비공식 엔드포인트라 복잡도가 크다 - 향후 확장 범위).
 * docs/content_extraction.md 참고.
 */
@Order(1)
@Component
public class YouTubeExtractionStrategy implements ExtractionStrategy {

    private static final String USER_AGENT =
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            + "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";
    private static final int TIMEOUT_MS = 10_000;

    @Override
    public boolean supports(URI uri) {
        String host = uri.getHost();
        if (host == null) {
            return false;
        }
        return host.endsWith("youtube.com") || host.equals("youtu.be");
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
            return ExtractionResult.failed(SourceType.YOUTUBE, FailureReason.TIMEOUT);
        } catch (HttpStatusException e) {
            FailureReason reason = (e.getStatusCode() == 403 || e.getStatusCode() == 401)
                ? FailureReason.ROBOTS_BLOCKED
                : FailureReason.NETWORK_ERROR;
            return ExtractionResult.failed(SourceType.YOUTUBE, reason);
        } catch (IOException e) {
            return ExtractionResult.failed(SourceType.YOUTUBE, FailureReason.NETWORK_ERROR);
        }

        String ogTitle = document.select("meta[property=og:title]").attr("content");
        String ogDescription = document.select("meta[property=og:description]").attr("content");
        String title = !ogTitle.isBlank() ? ogTitle : document.title();

        if (!ogDescription.isBlank()) {
            return ExtractionResult.success(title, ogDescription, SourceType.YOUTUBE);
        }

        if (!title.isBlank()) {
            return ExtractionResult.openGraphOnly(title, title, SourceType.YOUTUBE);
        }

        return ExtractionResult.failed(SourceType.YOUTUBE, FailureReason.EMPTY_CONTENT);
    }
}
