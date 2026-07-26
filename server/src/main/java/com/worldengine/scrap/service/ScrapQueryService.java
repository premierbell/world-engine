package com.worldengine.scrap.service;

import com.worldengine.scrap.dto.ScrapDetailResponse;
import com.worldengine.scrap.dto.ScrapStatsResponse;
import com.worldengine.scrap.dto.ScrapSummaryResponse;
import com.worldengine.scrap.entity.Scrap;
import com.worldengine.scrap.repository.ScrapRepository;
import jakarta.persistence.EntityNotFoundException;
import java.util.List;
import org.springframework.stereotype.Service;

@Service
public class ScrapQueryService {

    private final ScrapRepository scrapRepository;

    public ScrapQueryService(ScrapRepository scrapRepository) {
        this.scrapRepository = scrapRepository;
    }

    public List<ScrapSummaryResponse> findAll(Boolean confirmed) {
        List<Scrap> scraps;
        if (confirmed == null) {
            scraps = scrapRepository.findAll();
        } else if (confirmed) {
            scraps = scrapRepository.findByIslandIdIsNotNull();
        } else {
            scraps = scrapRepository.findByIslandIdIsNull();
        }
        return scraps.stream().map(this::toSummary).toList();
    }

    public ScrapStatsResponse computeStats() {
        List<Scrap> all = scrapRepository.findAll();
        long total = all.size();
        long confirmed = all.stream().filter(s -> s.getIslandId() != null).count();
        long unconfirmed = total - confirmed;

        List<Scrap> confirmedWithRecommendation = all.stream()
            .filter(s -> s.getIslandId() != null && s.getRecommendedIslandId() != null)
            .toList();

        long accepted = confirmedWithRecommendation.stream().filter(s -> !s.wasCorrected()).count();
        long overridden = confirmedWithRecommendation.stream().filter(Scrap::wasCorrected).count();
        long coldStart = all.stream()
            .filter(s -> s.getIslandId() != null && s.getRecommendedIslandId() == null)
            .count();

        int recommendedTotal = confirmedWithRecommendation.size();
        Double acceptanceRate = recommendedTotal == 0 ? null : (double) accepted / recommendedTotal;
        Double overrideRate = recommendedTotal == 0 ? null : (double) overridden / recommendedTotal;

        return new ScrapStatsResponse(
            total, confirmed, unconfirmed, accepted, overridden, coldStart, acceptanceRate, overrideRate);
    }

    public ScrapDetailResponse findById(Long id) {
        Scrap scrap = scrapRepository.findById(id)
            .orElseThrow(() -> new EntityNotFoundException("존재하지 않는 스크랩: " + id));

        return new ScrapDetailResponse(
            scrap.getId(),
            scrap.getUrl(),
            scrap.getTitle(),
            scrap.getSummary(),
            scrap.getSourceType(),
            scrap.getFallbackLevel(),
            scrap.getUserContext(),
            scrap.getIslandId(),
            scrap.getRecommendedIslandId(),
            scrap.wasCorrected(),
            scrap.getCreatedAt()
        );
    }

    private ScrapSummaryResponse toSummary(Scrap scrap) {
        return new ScrapSummaryResponse(
            scrap.getId(), scrap.getUrl(), scrap.getTitle(), scrap.getIslandId(), scrap.wasCorrected(), scrap.getCreatedAt());
    }
}
