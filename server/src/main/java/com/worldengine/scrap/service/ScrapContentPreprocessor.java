package com.worldengine.scrap.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class ScrapContentPreprocessor {

    private final int maxLength;

    public ScrapContentPreprocessor(@Value("${scrap.max-summary-length}") int maxLength) {
        this.maxLength = maxLength;
    }

    public String truncate(String content) {
        if (content == null || content.length() <= maxLength) {
            return content;
        }
        return content.substring(0, maxLength);
    }

}
