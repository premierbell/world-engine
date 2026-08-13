package com.worldengine.scrap.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class ScrapContentPreprocessor {

    private final int maxLength;
    private final int maxFullPageLength;

    public ScrapContentPreprocessor(
        @Value("${scrap.max-summary-length}") int maxLength,
        @Value("${scrap.max-fullpage-length}") int maxFullPageLength) {
        this.maxLength = maxLength;
        this.maxFullPageLength = maxFullPageLength;
    }

    public String truncate(String content) {
        return truncate(content, maxLength);
    }

    // ContentSummaryClient.summarizeFullPage() 2차 폴백용 - readability4j가
    // 놓친 내용을 찾아야 하니 1차 요약(maxLength)보다 더 넓은 창을 준다.
    public String truncateFullPage(String content) {
        return truncate(content, maxFullPageLength);
    }

    private String truncate(String content, int limit) {
        if (content == null || content.length() <= limit) {
            return content;
        }
        return content.substring(0, limit);
    }

}
