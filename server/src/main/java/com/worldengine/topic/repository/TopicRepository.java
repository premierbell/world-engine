package com.worldengine.topic.repository;

import com.worldengine.topic.entity.Topic;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TopicRepository extends JpaRepository<Topic, Long> {
    List<Topic> findByIslandId(Long islandId);

}
