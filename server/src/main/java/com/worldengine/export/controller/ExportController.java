package com.worldengine.export.controller;

import com.worldengine.export.dto.WorldExportResponse;
import com.worldengine.export.service.ExportService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/export")
public class ExportController {

    private final ExportService exportService;

    public ExportController(ExportService exportService) {
        this.exportService = exportService;
    }

    @GetMapping
    public WorldExportResponse export() {
        return exportService.export();
    }
}
