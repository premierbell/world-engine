package com.worldengine.island.repository;

import com.worldengine.island.entity.Island;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IslandRepository extends JpaRepository<Island, Long> {

}
