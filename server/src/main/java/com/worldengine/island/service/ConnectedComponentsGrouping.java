package com.worldengine.island.service;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

/**
 * threshold 이상인 쌍을 전부 연결해서 Union-Find로 묶는다 - 가장 단순하지만
 * 체이닝(Finding #010)에 취약함이 실제 데이터로 확인됨(PR #80,
 * experiments/v0_validation.md). CliqueSafeGrouping과 비교하기 위해
 * 남겨둔다 - 기본 전략은 아님.
 */
@Component
public class ConnectedComponentsGrouping implements TopicGroupingStrategy {

    @Override
    public List<List<Integer>> group(int itemCount, double[][] scores, double threshold) {
        int[] parent = new int[itemCount];
        for (int i = 0; i < itemCount; i++) {
            parent[i] = i;
        }

        for (int i = 0; i < itemCount; i++) {
            for (int j = i + 1; j < itemCount; j++) {
                if (scores[i][j] >= threshold) {
                    union(parent, i, j);
                }
            }
        }

        Map<Integer, List<Integer>> byRoot = new HashMap<>();
        for (int i = 0; i < itemCount; i++) {
            byRoot.computeIfAbsent(find(parent, i), k -> new ArrayList<>()).add(i);
        }
        return new ArrayList<>(byRoot.values());
    }

    private int find(int[] parent, int x) {
        if (parent[x] != x) {
            parent[x] = find(parent, parent[x]);
        }
        return parent[x];
    }

    private void union(int[] parent, int a, int b) {
        int rootA = find(parent, a);
        int rootB = find(parent, b);
        if (rootA != rootB) {
            parent[rootA] = rootB;
        }
    }
}
