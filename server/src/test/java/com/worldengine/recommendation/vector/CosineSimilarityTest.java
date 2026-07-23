package com.worldengine.recommendation.vector;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.junit.jupiter.api.Test;

class CosineSimilarityTest {

    @Test
    void identicalVectorsHaveSimilarityOne() {
        float[] v = {1f, 2f, 3f};
        assertEquals(1.0, CosineSimilarity.similarity(v, v), 1e-9);
    }

    @Test
    void orthogonalVectorsHaveSimilarityZero() {
        float[] a = {1f, 0f};
        float[] b = {0f, 1f};
        assertEquals(0.0, CosineSimilarity.similarity(a, b), 1e-9);
    }

    @Test
    void findTopKReturnsHighestSimilarityFirst() {
        float[] query = {1f, 0f};
        List<VectorCandidate> candidates = List.of(
            new VectorCandidate("far", new float[]{-1f, 0f}),
            new VectorCandidate("close", new float[]{0.9f, 0.1f}),
            new VectorCandidate("mid", new float[]{0.5f, 0.5f})
        );

        List<SimilarityResult> top2 = CosineSimilarity.findTopK(query, candidates, 2);

        assertEquals(2, top2.size());
        assertEquals("close", top2.get(0).id());
        assertEquals("mid", top2.get(1).id());
    }

    @Test
    void kLargerThanCandidateListReturnsAllCandidates() {
        List<VectorCandidate> candidates = List.of(new VectorCandidate("only", new float[]{1f, 0f}));

        List<SimilarityResult> result = CosineSimilarity.findTopK(new float[]{1f, 0f}, candidates, 5);

        assertEquals(1, result.size());
    }

    @Test
    void emptyCandidateListReturnsEmptyResult() {
        List<SimilarityResult> result = CosineSimilarity.findTopK(new float[]{1f, 0f}, List.of(), 3);

        assertTrue(result.isEmpty());
    }
}
