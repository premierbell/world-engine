package com.worldengine.recommendation.client;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

@Tag("live")
class OpenAiEmbeddingClientLiveTest {

    private final OpenAiEmbeddingClient client = new OpenAiEmbeddingClient(
        System.getenv("OPENAI_API_KEY"),
        "text-embedding-3-small"
    );

    @Test
    void embedsTextInto1536Dimensions() {
        float[] vector = client.embed("Docker는 컨테이너 기반 가상화 플랫폼이다.");

        assertNotNull(vector);
        assertEquals(1536, vector.length);
    }

}
