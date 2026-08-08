package com.worldengine.island.service;

import com.worldengine.island.dto.IslandDetailResponse;
import com.worldengine.island.dto.IslandSummaryResponse;
import com.worldengine.island.entity.Island;
import com.worldengine.island.model.GrowthTier;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.recommendation.vector.CosineSimilarity;
import com.worldengine.scrap.dto.ScrapSummaryResponse;
import com.worldengine.scrap.entity.Scrap;
import com.worldengine.scrap.repository.ScrapRepository;
import com.worldengine.topic.dto.TopicSummaryResponse;
import com.worldengine.topic.repository.TopicRepository;
import jakarta.persistence.EntityNotFoundException;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.stream.IntStream;
import org.springframework.stereotype.Service;

@Service
public class IslandQueryService {

    private final IslandRepository islandRepository;
    private final ScrapRepository scrapRepository;
    private final TopicRepository topicRepository;
    private final MapCoordinateService mapCoordinateService;

    public IslandQueryService(
        IslandRepository islandRepository,
        ScrapRepository scrapRepository,
        TopicRepository topicRepository,
        MapCoordinateService mapCoordinateService) {
        this.islandRepository = islandRepository;
        this.scrapRepository = scrapRepository;
        this.topicRepository = topicRepository;
        this.mapCoordinateService = mapCoordinateService;
    }

    public List<IslandSummaryResponse> findAll() {
        List<Island> islands = islandRepository.findAll();
        int totalCount = islands.size();

        return IntStream.range(0, totalCount)
            .mapToObj(index -> {
                Island island = islands.get(index);
                MapCoordinateService.Coordinate coordinate = mapCoordinateService.getCoordinate(island, index, totalCount);
                long scrapCount = scrapRepository.countByIslandId(island.getId());
                return new IslandSummaryResponse(
                    island.getId(),
                    island.getName(),
                    scrapCount,
                    topicRepository.countByIslandId(island.getId()),
                    coordinate.x(),
                    coordinate.y(),
                    GrowthTier.fromScrapCount(scrapCount));
            })
            .toList();
    }

    public IslandDetailResponse findById(Long islandId) {
        Island island = islandRepository.findById(islandId)
            .orElseThrow(() -> new EntityNotFoundException("존재하지 않는 Island: " + islandId));

        List<Scrap> islandScraps = scrapRepository.findByIslandId(islandId);
        List<ScrapSummaryResponse> scraps = islandScraps.stream()
            .map(this::toSummary)
            .toList();

        List<TopicSummaryResponse> topics = topicRepository.findByIslandId(islandId).stream()
            .map(topic -> new TopicSummaryResponse(
                topic.getId(),
                topic.getName(),
                islandScraps.stream()
                    .filter(s -> topic.getId().equals(s.getTopicId()))
                    .map(this::toSummary)
                    .toList()))
            .toList();

        return new IslandDetailResponse(
            island.getId(),
            island.getName(),
            scraps,
            computeCosineVariance(islandScraps),
            computeOverrideRate(islandScraps),
            topics
        );
    }

    private ScrapSummaryResponse toSummary(Scrap scrap) {
        return new ScrapSummaryResponse(scrap.getId(), scrap.getUrl(), scrap.getTitle(),
            scrap.getIslandId(), scrap.wasCorrected(), scrap.getCreatedAt());
    }

    /**
     * V2 관찰 신호(docs/v2_design.md) - Island 내부 scrap embedding들이 서로 얼마나
     * 흩어져 있는지. 판단 기준이 아니라 참고 정보 - 사용자가 직접 보고 판단한다.
     */
    private Double computeCosineVariance(List<Scrap> scraps) {
        List<float[]> embeddings = scraps.stream()
            .map(Scrap::getEmbedding)
            .filter(Objects::nonNull)
            .toList();

        if (embeddings.size() < 2) {
            return null;
        }

        List<Double> pairwiseSimilarities = new ArrayList<>();
        for (int i = 0;  i < embeddings.size(); i++) {
            for (int j = i + 1; j < embeddings.size(); j++) {
                pairwiseSimilarities.add(CosineSimilarity.similarity(embeddings.get(i), embeddings.get(j)));
            }
        }

        double mean = pairwiseSimilarities.stream().mapToDouble(Double::doubleValue).average().orElse(0.0);
        return pairwiseSimilarities.stream()
            .mapToDouble(s -> Math.pow(s - mean, 2))
            .average()
            .orElse(0.0);
    }

    /**
     * V2 관찰 신호 - 이 Island로 확정된 스크랩 중, 추천 1순위가 이 Island가 아니었던
     * 비율(/scraps/stats의 overrideRate와 같은 계산을 Island 단위로 좁힌 것).
     */
    private Double computeOverrideRate(List<Scrap> scraps) {
        List<Scrap> withRecommendation = scraps.stream()
            .filter(s -> s.getRecommendedIslandId() != null)
            .toList();

        if (withRecommendation.isEmpty()) {
            return null;
        }

        long overridden = withRecommendation.stream().filter(Scrap::wasCorrected).count();
        return (double) overridden / withRecommendation.size();
    }
}
