package com.worldengine.scrap.controller;

import com.worldengine.recommendation.service.IslandRecommendation;
import com.worldengine.scrap.dto.ScrapConfirmRequest;
import com.worldengine.scrap.dto.ScrapConfirmResponse;
import com.worldengine.scrap.dto.ScrapCreateRequest;
import com.worldengine.scrap.dto.ScrapCreateResponse;
import com.worldengine.scrap.dto.ScrapDetailResponse;
import com.worldengine.scrap.dto.ScrapStatsResponse;
import com.worldengine.scrap.dto.ScrapSummaryResponse;
import com.worldengine.scrap.service.ScrapConfirmService;
import com.worldengine.scrap.service.ScrapQueryService;
import com.worldengine.scrap.service.ScrapService;
import java.util.List;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/scraps")
public class ScrapController {

    private final ScrapService scrapService;
    private final ScrapConfirmService scrapConfirmService;
    private final ScrapQueryService scrapQueryService;

    public ScrapController(ScrapService scrapService, ScrapConfirmService scrapConfirmService, ScrapQueryService scrapQueryService) {
        this.scrapService = scrapService;
        this.scrapConfirmService = scrapConfirmService;
        this.scrapQueryService = scrapQueryService;
    }

    @PostMapping
    public ScrapCreateResponse createScrap(@RequestBody ScrapCreateRequest request) {
        boolean force = Boolean.TRUE.equals(request.force());
        return scrapService.createScrap(request.url(), request.userContext(), force);
    }

    @PostMapping("/{id}/confirm")
    public ScrapConfirmResponse confirmIsland(@PathVariable Long id, @RequestBody ScrapConfirmRequest request) {
        return scrapConfirmService.confirm(id, request.islandId(), request.newIslandName());
    }

    @GetMapping
    public List<ScrapSummaryResponse> listScraps(@RequestParam(required = false) Boolean confirmed) {
        return scrapQueryService.findAll(confirmed);
    }

    @PostMapping("/{id}/recommendations")
    public List<IslandRecommendation> refreshRecommendations(@PathVariable Long id) {
        return scrapService.refreshRecommendations(id);
    }

    @PostMapping("/{id}/resummarize")
    public ScrapCreateResponse resummarize(@PathVariable Long id) {
        return scrapService.resummarize(id);
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable Long id) {
        scrapService.delete(id);
    }

    @GetMapping("/stats")
    public ScrapStatsResponse getStats() {
        return scrapQueryService.computeStats();
    }

    @GetMapping("/{id}")
    public ScrapDetailResponse getScrap(@PathVariable Long id) {
        return scrapQueryService.findById(id);
    }
}