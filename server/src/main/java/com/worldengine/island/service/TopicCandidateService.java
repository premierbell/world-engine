package com.worldengine.island.service;

import com.worldengine.island.dto.ExistingTopicMatch;
import com.worldengine.island.dto.TopicCandidateGroup;
import com.worldengine.island.dto.TopicCandidateResponse;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.recommendation.client.LlmPairwiseJudgeClient;
import com.worldengine.scrap.dto.ScrapSummaryResponse;
import com.worldengine.scrap.entity.Scrap;
import com.worldengine.scrap.repository.ScrapRepository;
import com.worldengine.topic.entity.Topic;
import com.worldengine.topic.repository.TopicRepository;
import jakarta.persistence.EntityNotFoundException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;

/**
 * docs/v2_design.md의 Topic 후보 생성 - AI는 후보만 만든다, 저장/승인은
 * 다음 단계다. Grouping 알고리즘은 TopicGroupingStrategy로 분리해서
 * 나중에도 비교/교체 가능하게 유지한다.
 *
 * 미분류 스크랩은 두 단계로 처리한다 - 먼저 기존 Topic 멤버들과 비교해서
 * "이미 있는 Topic에 어울리는가"를 본다(멤버 중 최고점 기준). 매칭된
 * 스크랩은 새 후보 그룹 탐색에서 제외한다 - 정말 새로운 주제만 Clique-safe
 * 그룹핑 대상이 된다.
 *
 * 두 단계 모두 pairwise 채점은 서로 독립적인 호출이라 병렬로 돌린다(실측:
 * 22개 Island 기준 순차 3분 가까이 걸림, experiments/v0_validation.md
 * 참고) - 알고리즘/결과는 그대로 두고 실행 방식만 바꾸는 가장 작은 변경.
 * 각 계산은 서로 다른 배열 칸에만 쓰기 때문에 동기화 없이도 안전하고,
 * 각 단계가 끝날 때 전부 join한 뒤에만 결과를 읽는다. 두 단계는 서로
 * 의존적이라(2단계가 1단계의 remaining을 씀) 순차로 유지한다.
 */
@Service
public class TopicCandidateService {

    private static final double GROUPING_THRESHOLD = 0.6;
    private static final int PARALLELISM = 2;

    private final IslandRepository islandRepository;
    private final ScrapRepository scrapRepository;
    private final TopicRepository topicRepository;
    private final LlmPairwiseJudgeClient llmPairwiseJudgeClient;
    private final TopicGroupingStrategy groupingStrategy;

    public TopicCandidateService(
        IslandRepository islandRepository,
        ScrapRepository scrapRepository,
        TopicRepository topicRepository,
        LlmPairwiseJudgeClient llmPairwiseJudgeClient,
        TopicGroupingStrategy groupingStrategy) {
        this.islandRepository = islandRepository;
        this.scrapRepository = scrapRepository;
        this.topicRepository = topicRepository;
        this.llmPairwiseJudgeClient = llmPairwiseJudgeClient;
        this.groupingStrategy = groupingStrategy;
    }

    public TopicCandidateResponse generateCandidates(Long islandId) {
        islandRepository.findById(islandId)
            .orElseThrow(() -> new EntityNotFoundException("존재하지 않는 Island: " + islandId));

        List<Scrap> allScraps = scrapRepository.findByIslandId(islandId).stream()
            .filter(s -> s.getSummary() != null && !s.getSummary().isBlank())
            .toList();

        List<Topic> existingTopics = topicRepository.findByIslandId(islandId);
        Map<Long, List<Scrap>> membersByTopicId = allScraps.stream()
            .filter(s -> s.getTopicId() != null)
            .collect(Collectors.groupingBy(Scrap::getTopicId));

        List<Scrap> unassigned = allScraps.stream()
            .filter(s -> s.getTopicId() == null)
            .toList();

        try (ExecutorService executor = Executors.newFixedThreadPool(PARALLELISM)) {
            List<MatchTask> tasks = new ArrayList<>();
            for (int i = 0; i < unassigned.size(); i++) {
                for (Topic topic : existingTopics) {
                    for (Scrap member : membersByTopicId.getOrDefault(topic.getId(), List.of())) {
                        tasks.add(new MatchTask(i, topic, member));
                    }
                }
            }

            double[] taskScores = new double[tasks.size()];
            List<CompletableFuture<Void>> matchFutures = new ArrayList<>();
            for (int t = 0; t < tasks.size(); t++) {
                int taskIndex = t;
                MatchTask task = tasks.get(t);
                matchFutures.add(CompletableFuture.runAsync(() -> {
                    taskScores[taskIndex] = llmPairwiseJudgeClient.scoreMechanism(
                        unassigned.get(task.scrapIndex()).getSummary(), task.member().getSummary());
                }, executor));
            }
            matchFutures.forEach(CompletableFuture::join);

            ExistingTopicMatch[] bestPerScrap = new ExistingTopicMatch[unassigned.size()];
            for (int t = 0; t < tasks.size(); t++) {
                MatchTask task = tasks.get(t);
                double score = taskScores[t];
                if (score >= GROUPING_THRESHOLD) {
                    ExistingTopicMatch current = bestPerScrap[task.scrapIndex()];
                    if (current == null || score > current.score()) {
                        bestPerScrap[task.scrapIndex()] = new ExistingTopicMatch(
                            toSummary(unassigned.get(task.scrapIndex())), task.topic().getId(),
                            task.topic().getName(), score, toSummary(task.member()));
                    }
                }
            }

            List<ExistingTopicMatch> existingTopicMatches = new ArrayList<>();
            List<Scrap> remaining = new ArrayList<>();
            for (int i = 0; i < unassigned.size(); i++) {
                if (bestPerScrap[i] != null) {
                    existingTopicMatches.add(bestPerScrap[i]);
                } else {
                    remaining.add(unassigned.get(i));
                }
            }

            int n = remaining.size();
            double[][] scores = new double[n][n];

            List<int[]> pairs = new ArrayList<>();
            for (int i = 0; i < n; i++) {
                for (int j = i + 1; j < n; j++) {
                    pairs.add(new int[]{i, j});
                }
            }

            List<CompletableFuture<Void>> pairFutures = pairs.stream()
                .map(pair -> CompletableFuture.runAsync(() -> {
                    double score = llmPairwiseJudgeClient.scoreMechanism(
                        remaining.get(pair[0]).getSummary(), remaining.get(pair[1]).getSummary());
                    scores[pair[0]][pair[1]] = score;
                    scores[pair[1]][pair[0]] = score;
                }, executor))
                .toList();
            pairFutures.forEach(CompletableFuture::join);

            List<List<Integer>> memberGroups = groupingStrategy.group(n, scores, GROUPING_THRESHOLD);

            List<TopicCandidateGroup> groups = new ArrayList<>();
            List<ScrapSummaryResponse> ungrouped = new ArrayList<>();

            for (List<Integer> members : memberGroups) {
                if (members.size() < 2) {
                    ungrouped.add(toSummary(remaining.get(members.get(0))));
                    continue;
                }
                List<Double> pairScores = new ArrayList<>();
                for (int a = 0; a < members.size(); a++) {
                    for (int b = a + 1; b < members.size(); b++) {
                        pairScores.add(scores[members.get(a)][members.get(b)]);
                    }
                }
                double average = pairScores.stream().mapToDouble(Double::doubleValue).average()
                    .orElse(0.0);
                double minimum = pairScores.stream().mapToDouble(Double::doubleValue).min().orElse(0.0);
                List<ScrapSummaryResponse> groupScraps = members.stream()
                    .map(idx -> toSummary(remaining.get(idx)))
                    .toList();
                groups.add(new TopicCandidateGroup(groupScraps, average, minimum));
            }

            return new TopicCandidateResponse(existingTopicMatches, groups, ungrouped);
        }
    }

    private ScrapSummaryResponse toSummary(Scrap scrap) {
        return new ScrapSummaryResponse(scrap.getId(), scrap.getUrl(), scrap.getTitle(),
            scrap.getIslandId(), scrap.wasCorrected(), scrap.getCreatedAt());
    }

    private record MatchTask(int scrapIndex, Topic topic, Scrap member) {}
}