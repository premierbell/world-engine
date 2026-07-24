package com.worldengine.island.controller;

import com.worldengine.island.dto.IslandDetailResponse;
import com.worldengine.island.dto.IslandSummaryResponse;
import com.worldengine.island.service.IslandQueryService;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/islands")
public class IslandController {

    private final IslandQueryService islandQueryService;

    public IslandController(IslandQueryService islandQueryService) {
        this.islandQueryService = islandQueryService;
    }

    @GetMapping
    public List<IslandSummaryResponse> listIslands() {
        return islandQueryService.findAll();
    }

    @GetMapping("/{id}")
    public IslandDetailResponse getIsland(@PathVariable Long id) {
        return islandQueryService.findById(id);
    }
}
