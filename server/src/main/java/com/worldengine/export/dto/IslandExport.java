package com.worldengine.export.dto;

public record IslandExport(
    Long id,
    String name,
    Double x,
    Double y,
    float[] embedding
) {}
