package com.worldengine.scrap.service;

import com.worldengine.scrap.dto.ScrapDetailResponse;
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

    public List<ScrapSummaryResponse> findAll() {
        return scrapRepository.findAll().stream()
            .map(this::toSummary)
            .toList();
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
