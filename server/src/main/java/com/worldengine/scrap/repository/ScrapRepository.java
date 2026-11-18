package com.worldengine.scrap.repository;

import com.worldengine.scrap.entity.Scrap;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ScrapRepository extends JpaRepository<Scrap, Long> {

    List<Scrap> findByIslandId(Long islandId);

    /**
     * 섬 멤버의 id·summary·embedding만 조회한다 - 엔티티를 만들지 않고 본문도 읽지 않는다.
     * 임베딩이 없는 멤버(추출 실패, BOILERPLATE_ONLY)는 쿼리에서 제외한다.
     */
    @Query("""
        select new com.worldengine.scrap.repository.IslandMemberVector(s.id, s.summary, s.embedding)
        from Scrap s
        where s.islandId = :islandId and s.embedding is not null
        """)
    List<IslandMemberVector> findMemberVectorsByIslandId(@Param("islandId") Long islandId);

    long countByIslandId(Long islandId);

    List<Scrap> findByIslandIdIsNull();

    List<Scrap> findByIslandIdIsNotNull();

    List<Scrap> findByTopicId(Long topicId);

    Optional<Scrap> findByUrl(String url);
}
