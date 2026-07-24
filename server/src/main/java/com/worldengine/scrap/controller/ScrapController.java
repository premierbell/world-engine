package com.worldengine.scrap.controller;

import com.worldengine.scrap.dto.ScrapCreateRequest;
import com.worldengine.scrap.dto.ScrapCreateResponse;
import com.worldengine.scrap.service.ScrapService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/scraps")
public class ScrapController {

    private final ScrapService scrapService;

    public ScrapController(ScrapService scrapService) {
        this.scrapService = scrapService;
    }

    @PostMapping
    public ScrapCreateResponse createScrap(@RequestBody ScrapCreateRequest request) {
        return scrapService.createScrap(request.url(), request.userContext());
    }
}
