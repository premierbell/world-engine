package com.worldengine.scrap.entity;

import com.worldengine.common.jpa.EmbeddingConverter;
import com.worldengine.extraction.model.FallbackLevel;
import com.worldengine.extraction.model.SourceType;
import jakarta.persistence.Column;
import jakarta.persistence.Convert;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import java.time.Instant;

@Entity
public class Scrap {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String url;

    private String title;

    @Column(columnDefinition = "TEXT")
    private String content;

    @Column(columnDefinition = "TEXT")
    private String summary;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private SourceType sourceType;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private FallbackLevel fallbackLevel;

    private String userContext;

    @Convert(converter = EmbeddingConverter.class)
    @Column(columnDefinition = "TEXT")
    private float[] embedding;

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    private Long islandId;

    private Long recommendedIslandId;

    protected Scrap() {}

    public Scrap(String url, String title, String content, String summary,
        SourceType sourceType, FallbackLevel fallbackLevel,
        String userContext, float[] embedding) {
        this.url = url;
        this.title = title;
        this.content = content;
        this.summary = summary;
        this.sourceType = sourceType;
        this.fallbackLevel = fallbackLevel;
        this.userContext = userContext;
        this.embedding = embedding;
        this.createdAt = Instant.now();
    }

    public Long getId() {
        return id;
    }

    public String getUrl() {
        return url;
    }

    public String getTitle() {
        return title;
    }

    public String getContent() {
        return content;
    }

    public String getSummary() {
        return summary;
    }

    public SourceType getSourceType() {
        return sourceType;
    }

    public FallbackLevel getFallbackLevel() {
        return fallbackLevel;
    }

    public String getUserContext() {
        return userContext;
    }

    public float[] getEmbedding() {
        return embedding;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Long getIslandId() { return islandId; }

    public void confirmIsland(Long islandId) { this.islandId = islandId; }

    public Long getRecommendedIslandId() { return recommendedIslandId; }

    public void recordRecommendedIsland(Long islandId) { this.recommendedIslandId = islandId; }

    public boolean wasCorrected() {
        return recommendedIslandId != null && islandId != null && !islandId.equals(recommendedIslandId);
    }
}
