package com.worldengine.island.service;

import java.util.List;

/**
 * pairwise 점수 행렬을 후보 그룹(인덱스 리스트)으로 바꾸는 전략 - 구현체를
 * 나중에도 쉽게 비교/교체할 수 있도록 인터페이스로 분리한다
 * (experiments/v0_validation.md의 Connected Components vs Clique-safe
 * vs Average-linkage 비교 참고).
 */
public interface TopicGroupingStrategy {
    List<List<Integer>> group(int itemCount, double[][] scores, double threshold);
}
