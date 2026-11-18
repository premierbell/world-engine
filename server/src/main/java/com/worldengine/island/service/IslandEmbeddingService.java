package com.worldengine.island.service;

import com.worldengine.island.entity.Island;
import com.worldengine.island.repository.IslandRepository;
import com.worldengine.scrap.repository.IslandMemberVector;
import com.worldengine.scrap.repository.ScrapRepository;
import jakarta.persistence.EntityNotFoundException;
import java.util.List;
import org.springframework.stereotype.Service;

/**
 * Island 대표 벡터를 "섬을 만든 첫 스크랩의 임베딩"이 아니라 "현재 멤버 임베딩의 평균"으로
 * 관리한다. 시간순 재현 평가(experiments/v0_validation.md, 2026-11-17)에서 첫 스크랩 고정
 * 방식은 Cosine 1순위 적중 83%, 멤버 평균은 96%였고, 기존 방식은 재요약(PR #139) 때
 * 섬 벡터가 갱신되지 않아 낡은 상태로 남아 있었다.
 *
 * 멤버가 바뀌거나(확정/이동/삭제) 멤버 임베딩이 바뀔 때(재요약) 이 서비스의 refresh()를
 * 호출한다. 추천할 때는 저장된 값만 읽으므로 스크랩이 늘어도 추천 비용은 늘지 않는다.
 */
@Service
public class IslandEmbeddingService {

    private final IslandRepository islandRepository;
    private final ScrapRepository scrapRepository;

    public IslandEmbeddingService(IslandRepository islandRepository, ScrapRepository scrapRepository) {
        this.islandRepository = islandRepository;
        this.scrapRepository = scrapRepository;
    }

    /**
     * 임베딩이 있는 멤버들의 평균으로 섬 벡터를 다시 계산한다. 평균을 낼 멤버가 없으면
     * (마지막 스크랩 삭제, 전부 임베딩 없음) 기존 벡터를 그대로 둔다 - embedding 컬럼이
     * NOT NULL이고, 빈 섬에도 앞으로 추천될 기준점은 남아 있어야 하기 때문.
     */
    public void refresh(Long islandId) {
        Island island = islandRepository.findById(islandId)
            .orElseThrow(() -> new EntityNotFoundException("존재하지 않는 Island: " + islandId));

        List<float[]> memberEmbeddings = scrapRepository.findMemberVectorsByIslandId(islandId).stream()
            .map(IslandMemberVector::embedding)
            .toList();

        if (memberEmbeddings.isEmpty()) {
            return;
        }

        island.updateEmbedding(mean(memberEmbeddings));
        islandRepository.save(island);
    }

    /** 전체 섬 재계산 - 기존 데이터 백필과, 나중에 어긋났을 때 복구용. 처리한 섬 개수를 반환. */
    public int refreshAll() {
        List<Island> islands = islandRepository.findAll();
        for (Island island : islands) {
            refresh(island.getId());
        }
        return islands.size();
    }

    private float[] mean(List<float[]> vectors) {
        int dimension = vectors.get(0).length;
        double[] sum = new double[dimension];
        for (float[] vector : vectors) {
            for (int i = 0; i < dimension; i++) {
                sum[i] += vector[i];
            }
        }

        float[] mean = new float[dimension];
        for (int i = 0; i < dimension; i++) {
            mean[i] = (float) (sum[i] / vectors.size());
        }
        return mean;
    }

}
