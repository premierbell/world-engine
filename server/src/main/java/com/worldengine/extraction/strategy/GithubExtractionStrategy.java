package com.worldengine.extraction.strategy;

import com.worldengine.extraction.model.ExtractionResult;
import com.worldengine.extraction.model.FailureReason;
import com.worldengine.extraction.model.SourceType;
import java.io.IOException;
import java.net.SocketTimeoutException;
import java.net.URI;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.jsoup.Connection;
import org.jsoup.HttpStatusException;
import org.jsoup.Jsoup;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/**
 * GitHub 저장소 - HTML 파싱 대신 GitHub REST API로 README를 직접
 * 요청한다(HTML 파싱보다 훨씬 안정적). README가 없으면 저장소
 * description으로 격하. 인증 없는 API 호출은 시간당 60회로 제한된다
 * (GitHub API rate limit) - 운영 단계에서는 personal access token
 * 도입을 고려해야 한다. docs/content_extraction.md 참고.
 */
@Order(1)
@Component
public class GithubExtractionStrategy implements ExtractionStrategy {

    private static final int TIMEOUT_MS = 10_000;
    private static final Pattern OWNER_REPO_PATTERN = Pattern.compile("^/([^/]+)/([^/]+)");

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public boolean supports(URI uri) {
        String host = uri.getHost();
        return host != null && (host.equals("github.com") || host.equals("www.github.com"));
    }

    @Override
    public ExtractionResult extract(URI uri) {
        Matcher matcher =  OWNER_REPO_PATTERN.matcher(uri.getPath());
        if (!matcher.find()) {
            return ExtractionResult.failed(SourceType.GITHUB, FailureReason.UNSUPPORTED_SOURCE);
        }
        String owner = matcher.group(1);
        String repo = matcher.group(2);

        String readme = fetchReadme(owner, repo);
        if (readme != null && !readme.isBlank()) {
            return ExtractionResult.success(owner + "/" + repo, readme.trim(), SourceType.GITHUB);
        }

        return fetchDescriptionFallback(owner, repo);
    }

    private String fetchReadme(String owner, String repo) {
        try {
            Connection.Response response = Jsoup.connect("https://api.github.com/repos/" + owner + "/" + repo + "/readme")
                .header("Accept", "application/vnd.github.raw+json")
                .timeout(TIMEOUT_MS)
                .ignoreContentType(true)
                .execute();
            return response.body();
        } catch (IOException e) {
            return null;
        }
    }

    private ExtractionResult fetchDescriptionFallback(String owner, String repo) {
        try{
            Connection.Response response = Jsoup.connect("https://api.github.com/repos/" + owner + "/" + repo)
                .timeout(TIMEOUT_MS)
                .ignoreContentType(true)
                .execute();
            JsonNode json = objectMapper.readTree(response.body());
            String description = json.path("description").asString(null);

            if (description == null || description.isBlank()) {
                return ExtractionResult.failed(SourceType.GITHUB, FailureReason.EMPTY_CONTENT);
            }
            return ExtractionResult.openGraphOnly(owner + "/" + repo, description,  SourceType.GITHUB);
        } catch (SocketTimeoutException e){
            return ExtractionResult.failed(SourceType.GITHUB, FailureReason.TIMEOUT);
        } catch (HttpStatusException e) {
            FailureReason reason = (e.getStatusCode() == 403 || e.getStatusCode() == 401)
                ? FailureReason.ROBOTS_BLOCKED
                :FailureReason.NETWORK_ERROR;
            return ExtractionResult.failed(SourceType.GITHUB, reason);
        } catch (IOException e) {
            return ExtractionResult.failed(SourceType.GITHUB, FailureReason.NETWORK_ERROR);
        }
    }
}
