package com.worldengine.extraction.model;

/**
 * Content Extraction의 출력 - 뒤 파이프라인(Summary/Embedding/추천)은
 * 이 레코드만 알면 된다. docs/content_extraction.md 참고.
 *
 * summaryCandidate는 이 단계에서 채우지 않는다 - LLM 기반 요약은 별도
 * 파이프라인 단계(V1 설계 참고)의 책임이다.
 */
public record ExtractionResult(
    ExtractionStatus status,
    String title,
    String content,
    String summaryCandidate,
    SourceType sourceType,
    FallbackLevel fallbackLevel,
    FailureReason failureReason
) {

    public static ExtractionResult success(String title, String content, SourceType sourceType) {
        return new ExtractionResult(
            ExtractionStatus.SUCCESS,
            title,
            content,
            null,
            sourceType,
            FallbackLevel.DIRECT_EXTRACTION,
            FailureReason.NONE
        );
    }

    public static ExtractionResult openGraphOnly(String title, String description, SourceType sourceType) {
        return new ExtractionResult(
            ExtractionStatus.PARTIAL,
            title,
            description,
            null,
            sourceType,
            FallbackLevel.OPEN_GRAPH_ONLY,
            FailureReason.NONE
        );
    }

    public static ExtractionResult failed(SourceType sourceType, FailureReason reason) {
        return new ExtractionResult(
            ExtractionStatus.FAILED,
            null,
            null,
            null,
            sourceType,
            FallbackLevel.EXTRACTION_FAILED,
            reason
        );
    }
}
