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
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

/**
 * docs/v2_design.md의 Topic 후보 생성 - AI는 후보만 만든다, 저장/승인은
 * 다음 단계다. connected components는 체이닝(Finding #010)에 취약할 수
 * 있어 그룹마다 평균/최소 pairwise score를 같이 반환한다 - 최소 점수가
 * 낮으면 체이닝이 실제 발생했다는 뜻이라 사용자가 눈으로 바로 판단할 수
 * 있다.
 */
@Service
public class TopicCandidateService {

    private static final double GROUPING_THRESHOLD = 0.6;

    private final IslandRepository islandRepository;
    private final ScrapRepository scrapRepository;
    private final LlmPairwiseJudgeClient llmPairwiseJudgeClient;

    public TopicCandidateService(
        IslandRepository islandRepository,
        ScrapRepository scrapRepository,
        LlmPairwiseJudgeClient llmPairwiseJudgeClient) {
        this.islandRepository = islandRepository;
        this.scrapRepository = scrapRepository;
        this.llmPairwiseJudgeClient = llmPairwiseJudgeClient;
    }

    public TopicCandidateResponse generateCandidates(Long islandId) {
        islandRepository.findById(islandId)
            .orElseThrow(() -> new EntityNotFoundException("존재하지 않는 Island: " + islandId));

        List<Scrap> scraps = scrapRepository.findByIslandId(islandId).stream()
            .filter(s -> s.getSummary() != null && !s.getSummary().isBlank())
            .toList();

        int n = scraps.size();
        double[][] scores = new double[n][n];
        UnionFind unionFind = new UnionFind(n);

        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                double score = llmPairwiseJudgeClient.scoreMechanism(
                    scraps.get(i).getSummary(), scraps.get(j).getSummary());
                scores[i][j] = score;
                scores[j][i] = score;
                if (score >= GROUPING_THRESHOLD) {
                    unionFind.union(i, j);
                }
            }
        }

        Map<Integer, List<Integer>> byRoot = new HashMap<>();
        for (int i = 0; i < n; i++) {
            byRoot.computeIfAbsent(unionFind.find(i), k -> new ArrayList<>()).add(i);
        }

        List<TopicCandidateGroup> groups = new ArrayList<>();
        List<ScrapSummaryResponse> ungrouped = new ArrayList<>();

        for (List<Integer> members : byRoot.values()) {
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

    private static final class UnionFind {
        private final int[] parent;

        UnionFind(int size) {
            parent = new int[size];
            for (int i = 0; i < size; i++) {
                parent[i] = i;
            }
        }

        int find(int x) {
            if (parent[x] != x) {
                parent[x] = find(parent[x]);
            }
            return parent[x];
        }

        void union(int a, int b) {
            int rootA = find(a);
            int rootB = find(b);
            if (rootA != rootB) {
                parent[rootA] = rootB;
            }
        }
    }
}
