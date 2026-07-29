package com.worldengine.topic.controller;

import com.worldengine.topic.dto.TopicCreateRequest;
import com.worldengine.topic.dto.TopicCreateResponse;
import com.worldengine.topic.service.TopicService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/topics")
public class TopicController {

    private final TopicService topicService;

    public TopicController(TopicService topicService) {
        this.topicService = topicService;
    }

    @PostMapping
    public TopicCreateResponse create(@RequestBody TopicCreateRequest request) {
        return topicService.create(request);
    }
}
