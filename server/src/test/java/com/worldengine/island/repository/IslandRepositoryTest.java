package com.worldengine.island.repository;

import static org.assertj.core.api.Assertions.assertThat;

import com.worldengine.island.entity.Island;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.data.jpa.test.autoconfigure.DataJpaTest;

@DataJpaTest
class IslandRepositoryTest {

    @Autowired
    private IslandRepository islandRepository;

    @Test
    void savesAndLoadsIslandWithEmbedding() {
        float[] embedding = {0.1f, 0.2f, 0.3f};
        Island saved = islandRepository.save(new Island("다이어트", embedding));

        Island found = islandRepository.findById(saved.getId()).orElseThrow();

        assertThat(found.getName()).isEqualTo("다이어트");
        assertThat(found.getEmbedding()).containsExactly(embedding);
    }

    @Test
    void deletesIsland() {
        Island saved = islandRepository.save(new Island("삭제될섬", new float[]{1f, 2f}));

        islandRepository.deleteById(saved.getId());

        assertThat(islandRepository.findById(saved.getId())).isEmpty();
    }
}
