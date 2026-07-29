package com.worldengine.island.service;

import com.worldengine.island.dto.TopicCandidateGroup;
import com.worldengine.island.dto.TopicCandidateResponse;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.recommendation.client.LlmPairwiseJudgeClient;
import com.worldengine.scrap.dto.ScrapSummaryResponse;
import com.worldengine.scrap.entity.Scrap;
import com.worldengine.scrap.repository.ScrapRepository;
import jakarta.persistence.EntityNotFoundException;
import java.util.ArrayList;
import java.util.List;
import org.springframework.stereotype.Service;

/**
 * docs/v2_design.md의 Topic 후보 생성 - AI는 후보만 만든다, 저장/승인은
 * 다음 단계다. Grouping 알고리즘은 TopicGroupingStrategy로 분리해서
 * 나중에도 비교/교체 가능하게 유지한다.
 */
@Service
public class TopicCandidateService {

    private static final double GROUPING_THRESHOLD = 0.6;

    private final IslandRepository islandRepository;
    private final ScrapRepository scrapRepository;
    private final LlmPairwiseJudgeClient llmPairwiseJudgeClient;
    private final TopicGroupingStrategy groupingStrategy;

    public TopicCandidateService(
        IslandRepository islandRepository,
        ScrapRepository scrapRepository,
        LlmPairwiseJudgeClient llmPairwiseJudgeClient,
        TopicGroupingStrategy groupingStrategy) {
        this.islandRepository = islandRepository;
        this.scrapRepository = scrapRepository;
        this.llmPairwiseJudgeClient = llmPairwiseJudgeClient;
        this.groupingStrategy = groupingStrategy;
    }

    public TopicCandidateResponse generateCandidates(Long islandId) {
        islandRepository.findById(islandId)
            .orElseThrow(() -> new EntityNotFoundException("존재하지 않는 Island: " + islandId));

        List<Scrap> scraps = scrapRepository.findByIslandId(islandId).stream()
            .filter(s -> s.getSummary() != null && !s.getSummary().isBlank())
            .toList();

        int n = scraps.size();
        double[][] scores = new double[n][n];

        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                double score = llmPairwiseJudgeClient.scoreMechanism(
                    scraps.get(i).getSummary(), scraps.get(j).getSummary());
                scores[i][j] = score;
                scores[j][i] = score;
            }
        }

        List<List<Integer>> memberGroups = groupingStrategy.group(n, scores, GROUPING_THRESHOLD);

        List<TopicCandidateGroup> groups = new ArrayList<>();
        List<ScrapSummaryResponse> ungrouped = new ArrayList<>();

        for (List<Integer> members : memberGroups) {
            if (members.size() < 2) {
                ungrouped.add(toSummary(scraps.get(members.get(0))));
                continue;
            }
            List<Double> pairScores = new ArrayList<>();
            for (int a = 0; a < members.size(); a++) {
                for (int b = a + 1; b < members.size(); b++) {
                    pairScores.add(scores[members.get(a)][members.get(b)]);
                }
            }
            double average = pairScores.stream().mapToDouble(Double::doubleValue).average().orElse(0.0);
            double minimum = pairScores.stream().mapToDouble(Double::doubleValue).min().orElse(0.0);
            List<ScrapSummaryResponse> groupScraps = members.stream()
                .map(idx -> toSummary(scraps.get(idx)))
                .toList();
            groups.add(new TopicCandidateGroup(groupScraps, average, minimum));
        }

        return new TopicCandidateResponse(groups, ungrouped);
    }

    private ScrapSummaryResponse toSummary(Scrap scrap) {
        return new ScrapSummaryResponse(scrap.getId(), scrap.getUrl(), scrap.getTitle(),
            scrap.getIslandId(), scrap.wasCorrected(), scrap.getCreatedAt());
    }
}
