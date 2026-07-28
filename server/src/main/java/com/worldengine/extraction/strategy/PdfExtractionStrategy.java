package com.worldengine.extraction.strategy;

import com.worldengine.extraction.model.ExtractionResult;
import com.worldengine.extraction.model.FailureReason;
import com.worldengine.extraction.model.SourceType;
import java.io.IOException;
import java.net.SocketTimeoutException;
import java.net.URI;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.jsoup.HttpStatusException;
import org.jsoup.Jsoup;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/**
 * PDF - 텍스트 레이어를 Apache PDFBox로 직접 추출한다. 스캔본처럼
 * 텍스트 레이어가 없는 PDF는 빈 문자열이 나오므로, 그 경우 URL의
 * 파일명을 제목/내용으로 대체한다. docs/content_extraction.md 참고.
 */
@Order(1)
@Component
public class PdfExtractionStrategy implements ExtractionStrategy{

    private static final String USER_AGENT =
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            + "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";
    private static final int TIMEOUT_MS = 15_000;
    private static final int MAX_BODY_SIZE_BYTES = 20 * 1024 * 1024; // 20MB

    @Override
    public boolean supports(URI uri) {
        String path = uri.getPath();
        return path != null && path.toLowerCase().endsWith(".pdf");
    }

    @Override
    public ExtractionResult extract(URI uri) {
        byte[] pdfBytes;
        try {
            pdfBytes = Jsoup.connect(uri.toString())
                .userAgent(USER_AGENT)
                .timeout(TIMEOUT_MS)
                .maxBodySize(MAX_BODY_SIZE_BYTES)
                .ignoreContentType(true)
                .execute()
                .bodyAsBytes();
        } catch (SocketTimeoutException e) {
            return ExtractionResult.failed(SourceType.PDF, FailureReason.TIMEOUT);
        } catch (HttpStatusException e) {
            FailureReason reason = (e.getStatusCode() == 403 || e.getStatusCode() == 401)
                ? FailureReason.ROBOTS_BLOCKED
                : FailureReason.NETWORK_ERROR;
            return ExtractionResult.failed(SourceType.PDF, reason);
        } catch (IOException e) {
            return ExtractionResult.failed(SourceType.PDF, FailureReason.NETWORK_ERROR);
        }

        String text;
        try (PDDocument document = Loader.loadPDF(pdfBytes)) {
            text = new PDFTextStripper().getText(document);
        } catch (IOException e) {
            // 손상되었거나 암호화된 PDF 등 - 파일명 fallback으로 넘어간다.
            text = null;
        }

        if (text != null) {
            // PDFBox가 표/양식 구조의 빈 셀 등을 NUL 문자로 추출하는 경우가 있는데,
            // Postgres는 TEXT/VARCHAR 컬럼에 NUL 바이트가 들어오면 저장 자체를 거부한다.
            text = text.replace("\u0000", "");
        }

        if (text != null && !text.isBlank()) {
            return ExtractionResult.success(fileNameOf(uri), text.trim(), SourceType.PDF);
        }

        String fileName = fileNameOf(uri);
        if (!fileName.isBlank()) {
            return ExtractionResult.openGraphOnly(fileName, fileName, SourceType.PDF);
        }
        return ExtractionResult.failed(SourceType.PDF, FailureReason.EMPTY_CONTENT);
    }

    private String fileNameOf(URI uri) {
        String path = uri.getPath();
        int lastSlash = path.lastIndexOf('/');
        return lastSlash >= 0 ? path.substring(lastSlash + 1) : path;
    }
}
