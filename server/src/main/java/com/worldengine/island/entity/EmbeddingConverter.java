package com.worldengine.island.entity;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;
import tools.jackson.databind.ObjectMapper;

@Converter
public class EmbeddingConverter implements AttributeConverter<float[], String> {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Override
    public String convertToDatabaseColumn(float[] embedding) {
        if (embedding == null) {
            return null;
        }
        return MAPPER.writeValueAsString(embedding);
    }

    @Override
    public float[] convertToEntityAttribute(String json) {
        if (json == null) {
            return null;
        }
        return MAPPER.readValue(json, float[].class);
    }
}
