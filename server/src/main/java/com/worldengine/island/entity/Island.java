package com.worldengine.island.entity;

import com.worldengine.common.jpa.EmbeddingConverter;
import jakarta.persistence.Column;
import jakarta.persistence.Convert;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;

@Entity
public class Island {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String name;

    @Convert(converter = EmbeddingConverter.class)
    @Column(nullable = false, columnDefinition = "TEXT")
    private float[] embedding;

    private Double x;

    private Double y;

    protected Island() {}

    public Island(String name, float[] embedding) {
        this.name = name;
        this.embedding = embedding;
    }

    public Long getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public float[] getEmbedding() {
        return embedding;
    }

    public Double getX() { return x; }

    public Double getY() { return y; }
}
