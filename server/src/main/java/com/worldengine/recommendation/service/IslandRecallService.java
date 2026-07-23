package com.worldengine.recommendation.service;

import com.worldengine.island.repository.IslandRepository;
import com.worldengine.recommendation.vector.CosineSimilarity;
import com.worldengine.recommendation.vector.SimilarityResult;
import com.worldengine.recommendation.vector.VectorCandidate;
import java.util.List;
import org.springframework.stereotype.Service;

@Service
public class IslandRecallService {

    private final IslandRepository islandRepository;

    public IslandRecallService(IslandRepository islandRepository) {
        this.islandRepository = islandRepository;
    }

    public List<SimilarityResult> recall(float[] queryEmbedding, int k) {
        List<VectorCandidate> candidates = islandRepository.findAll().stream()
            .map(island -> new VectorCandidate(String.valueOf(island.getId()), island.getEmbedding()))
            .toList();

        return CosineSimilarity.findTopK(queryEmbedding, candidates, k);
    }

}
