package com.worldengine.island.service;

import java.util.ArrayList;
import java.util.List;
import org.springframework.context.annotation.Primary;
import org.springframework.stereotype.Component;

/**
 * 새 항목은 기존 그룹 "전원"과 threshold 이상일 때만 편입된다(첫 번째로
 * 맞는 그룹에 그리디하게 배정 - 완전한 최대 클리크 탐색은 아니지만
 * 충분히 단순하고 체이닝을 구조적으로 막는다). Connected Components
 * 대비 실제 데이터에서 그룹 내부 최소 점수가 threshold 밑으로 떨어지는
 * 사례가 없어짐이 확인됨(experiments/v0_validation.md) - 기본 전략으로
 * 채택.
 */
@Component
@Primary
public class CliqueSafeGrouping implements TopicGroupingStrategy {

    @Override
    public List<List<Integer>> group(int itemCount, double[][] scores, double threshold) {
        List<List<Integer>> groups = new ArrayList<>();

        for (int i = 0; i < itemCount; i++) {
            List<Integer> target = null;
            for (List<Integer> group : groups) {
                if (fitsAll(group, i, scores, threshold)) {
                    target = group;
                    break;
                }
            }
            if (target != null) {
                target.add(i);
            } else {
                List<Integer> newGroup = new ArrayList<>();
                newGroup.add(i);
                groups.add(newGroup);
            }
        }
        return groups;
    }

    private boolean fitsAll(List<Integer> group, int candidate, double[][] scores, double threshold) {
        for (int member : group) {
            if (scores[candidate][member] < threshold) {
                return false;
            }
        }
        return true;
    }
}
