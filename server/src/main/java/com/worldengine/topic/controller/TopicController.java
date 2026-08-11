package com.worldengine.topic.controller;

import com.worldengine.topic.dto.TopicAddScrapsRequest;
import com.worldengine.topic.dto.TopicCreateRequest;
import com.worldengine.topic.dto.TopicCreateResponse;
import com.worldengine.topic.dto.TopicNameSuggestionRequest;
import com.worldengine.topic.dto.TopicNameSuggestionResponse;
import com.worldengine.topic.dto.TopicRenameRequest;
import com.worldengine.topic.dto.TopicRenameResponse;
import com.worldengine.topic.service.TopicNamingService;
import com.worldengine.topic.service.TopicService;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/topics")
public class TopicController {

    private final TopicService topicService;
    private final TopicNamingService topicNamingService;

    public TopicController(TopicService topicService, TopicNamingService topicNamingService) {
        this.topicService = topicService;
        this.topicNamingService = topicNamingService;
    }

    @PostMapping
    public TopicCreateResponse create(@RequestBody TopicCreateRequest request) {
        return topicService.create(request);
    }

    @PostMapping("/{id}/scraps")
    public TopicCreateResponse addScraps(@PathVariable Long id, @RequestBody TopicAddScrapsRequest request) {
        return topicService.addScraps(id, request);
    }

    @PatchMapping("/{id}")
    public TopicRenameResponse rename(@PathVariable Long id, @RequestBody TopicRenameRequest request) {
        return topicService.rename(id, request);
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable Long id) {
        topicService.delete(id);
    }

    @PostMapping("/suggest-name")
    public TopicNameSuggestionResponse suggestName(@RequestBody TopicNameSuggestionRequest request) {
        return topicNamingService.suggestName(request);
    }
}
