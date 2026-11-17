package com.worldengine.island.controller;

import com.worldengine.island.dto.IslandDetailResponse;
import com.worldengine.island.dto.IslandEmbeddingRecomputeResponse;
import com.worldengine.island.dto.IslandRenameRequest;
import com.worldengine.island.dto.IslandRenameResponse;
import com.worldengine.island.dto.IslandSummaryResponse;
import com.worldengine.island.dto.TopicCandidateResponse;
import com.worldengine.island.service.IslandEmbeddingService;
import com.worldengine.island.service.IslandQueryService;
import com.worldengine.island.service.IslandService;
import com.worldengine.island.service.TopicCandidateService;
import java.util.List;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/islands")
public class IslandController {

    private final IslandQueryService islandQueryService;
    private final IslandService islandService;
    private final TopicCandidateService topicCandidateService;
    private final IslandEmbeddingService islandEmbeddingService;

    public IslandController(
        IslandQueryService islandQueryService,
        IslandService islandService,
        TopicCandidateService topicCandidateService,
        IslandEmbeddingService islandEmbeddingService) {
        this.islandQueryService = islandQueryService;
        this.islandService = islandService;
        this.topicCandidateService = topicCandidateService;
        this.islandEmbeddingService = islandEmbeddingService;
    }

    @GetMapping
    public List<IslandSummaryResponse> listIslands() {
        return islandQueryService.findAll();
    }

    @GetMapping("/{id}")
    public IslandDetailResponse getIsland(@PathVariable Long id) {
        return islandQueryService.findById(id);
    }

    @PatchMapping("/{id}")
    public IslandRenameResponse rename(@PathVariable Long id, @RequestBody IslandRenameRequest request) {
        return islandService.rename(id, request);
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable Long id) {
        islandService.delete(id);
    }

    @PostMapping("/{id}/topic-candidates")
    public TopicCandidateResponse generateTopicCandidates(@PathVariable Long id) {
        return topicCandidateService.generateCandidates(id);
    }

    /**
     * 모든 섬의 대표 벡터를 현재 멤버 평균으로 다시 계산한다. 기존 데이터 백필(첫 스크랩 고정
     * 방식에서 전환)과, 나중에 섬 벡터가 어긋났을 때 복구용 - resummarize처럼 일회성이 아닌
     * 정식 엔드포인트로 둔다.
     */
    @PostMapping("/embeddings/recompute")
    public IslandEmbeddingRecomputeResponse recomputeEmbeddings() {
        return new IslandEmbeddingRecomputeResponse(islandEmbeddingService.refreshAll());
    }
}
