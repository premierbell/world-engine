package com.worldengine.extraction.service;

import com.worldengine.extraction.model.ExtractionResult;
import com.worldengine.extraction.model.FailureReason;
import com.worldengine.extraction.model.SourceType;
import com.worldengine.extraction.strategy.ExtractionStrategy;
import org.springframework.stereotype.Service;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.List;

/**
 * URL 하나를 받아 ExtractionResult를 반환하는 진입점. 등록된
 * ExtractionStrategy 중 supports()가 true인 첫 번째 전략에 위임한다 -
 * 리스트 순서가 라우팅 우선순위다(구체적인 전략을 앞에, ArticleExtractionStrategy처럼
 * 항상 true를 반환하는 기본값은 반드시 맨 뒤에 둘 것). docs/content_extraction.md 참고.
 */
@Service
public class ContentExtractionService {

    private final List<ExtractionStrategy> strategies;

    public ContentExtractionService(List<ExtractionStrategy> strategies) {
        this.strategies = strategies;
    }

    public ExtractionResult extract(String url) {
        URI uri;
        try {
            uri = new URI(url);
        } catch (URISyntaxException e) {
            return ExtractionResult.failed(SourceType.UNKNOWN, FailureReason.UNSUPPORTED_SOURCE);
        }

        return strategies.stream()
            .filter(strategy -> strategy.supports(uri))
            .findFirst()
            .map(strategy -> strategy.extract(uri))
            .orElseGet(() -> ExtractionResult.failed(SourceType.UNKNOWN, FailureReason.UNSUPPORTED_SOURCE));
    }
}
