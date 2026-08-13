package com.worldengine.scrap.service;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

public class ScrapContentPreprocessorTest {

    private final ScrapContentPreprocessor preprocessor = new ScrapContentPreprocessor(10, 20);

    @Test
    void returnsShortContentUnchanged() {
        assertThat(preprocessor.truncate("짧은 글")).isEqualTo("짧은 글");
    }

    @Test
    void truncatesContentLongerThanMaxLength() {
        String longContent = "0123456789ABCDEF";
        assertThat(preprocessor.truncate(longContent)).isEqualTo("0123456789");
    }

    @Test
    void returnsNullWhenContentIsNull() {
        assertThat(preprocessor.truncate(null)).isNull();
    }
}
