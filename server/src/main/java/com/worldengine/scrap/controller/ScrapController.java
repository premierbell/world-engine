package com.worldengine.scrap.controller;

import com.worldengine.scrap.dto.ScrapConfirmRequest;
import com.worldengine.scrap.dto.ScrapConfirmResponse;
import com.worldengine.scrap.dto.ScrapCreateRequest;
import com.worldengine.scrap.dto.ScrapCreateResponse;
import com.worldengine.scrap.dto.ScrapDetailResponse;
import com.worldengine.scrap.dto.ScrapSummaryResponse;
import com.worldengine.scrap.service.ScrapConfirmService;
import com.worldengine.scrap.service.ScrapQueryService;
import com.worldengine.scrap.service.ScrapService;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/scraps")
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
        return scrapService.createScrap(request.url(), request.userContext());
    }

    @PostMapping("/{id}/confirm")
    public ScrapConfirmResponse confirmIsland(@PathVariable Long id, @RequestBody ScrapConfirmRequest request) {
        return scrapConfirmService.confirm(id, request.islandId(), request.newIslandName());
    }

    @GetMapping
    public List<ScrapSummaryResponse> listScraps() {
        return scrapQueryService.findAll();
    }

    @GetMapping("/{id}")
    public ScrapDetailResponse getScrap(@PathVariable Long id) {
        return scrapQueryService.findById(id);
    }
}