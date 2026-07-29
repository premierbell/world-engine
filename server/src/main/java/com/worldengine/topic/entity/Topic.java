package com.worldengine.topic.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import java.time.Instant;

@Entity
public class Topic {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String name;

    @Column(nullable = false)
    private Long islandId;

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    protected Topic() {}

    public Topic(String name, Long islandId) {
        this.name = name;
        this.islandId = islandId;
        this.createdAt = Instant.now();
    }

    public Long getId() { return id; }

    public String getName() { return name; }

    public Long getIslandId() { return islandId; }

    public Instant getCreatedAt() { return createdAt; }
}
