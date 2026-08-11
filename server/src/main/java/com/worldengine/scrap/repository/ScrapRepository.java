package com.worldengine.scrap.repository;

import com.worldengine.scrap.entity.Scrap;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ScrapRepository extends JpaRepository<Scrap, Long> {

    List<Scrap> findByIslandId(Long islandId);

    long countByIslandId(Long islandId);

    List<Scrap> findByIslandIdIsNull();

    List<Scrap> findByIslandIdIsNotNull();

    List<Scrap> findByTopicId(Long topicId);

    Optional<Scrap> findByUrl(String url);
}
