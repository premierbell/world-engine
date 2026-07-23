package com.worldengine.recommendation.vector;

import java.util.Comparator;
import java.util.List;

/**
 * 순수 계산 유틸 - Spring Bean이 아니다(V0 Python의 compute_assignment_matrix()
 * 처럼 DB/컨텍스트 없이 입력→출력만 있는 함수). Island 영속성이 생기면
 * Repository → List<VectorCandidate> 변환만 추가하고 이 클래스는 그대로 쓴다.
 */
public final class CosineSimilarity {

    private CosineSimilarity() {}

    public static List<SimilarityResult> findTopK(float[] query, List<VectorCandidate> candidates, int k) {
        return candidates.stream()
            .map(c -> new SimilarityResult(c.id(), similarity(query, c.embedding())))
            .sorted(Comparator.comparingDouble(SimilarityResult::similarity).reversed())
            .limit(k)
            .toList();
    }

    public static double similarity(float[] a, float[] b) {
        if (a.length != b.length) {
            throw new IllegalArgumentException("벡터 차원이 다름: " + a.length + " vs " + b.length);
        }
        double dot = 0, normA = 0, normB = 0;
        for (int i = 0; i < a.length; i++) {
            dot += a[i] * b[i];
            normA += a[i] * a[i];
            normB += b[i] * b[i];
        }
        if (normA == 0 || normB == 0) {
            return 0.0;
        }
        return dot / (Math.sqrt(normA) * Math.sqrt(normB));
    }

}
