package com.worldengine.common.web;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class SpaForwardController {

    @GetMapping("/islands/**")
    public String forwardIslandRoutes() {
        return "forward:/index.html";
    }
}
