package com.rivet.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.sql.DataSource;
import java.sql.Connection;
import java.util.HashMap;
import java.util.Map;

/**
 * Health check controller.
 * Used to verify the API is running and can connect to the database.
 */
@RestController
@RequestMapping("/api/health")
public class HealthController {

    @Autowired
    private DataSource dataSource;

    @GetMapping
    public ResponseEntity<Map<String, Object>> health() {
        Map<String, Object> health = new HashMap<>();
        health.put("status", "UP");
        health.put("service", "Rivet CMMS API");
        health.put("version", "1.0.0");

        // Check database connectivity
        try (Connection connection = dataSource.getConnection()) {
            health.put("database", "UP");
            health.put("databaseProductName", connection.getMetaData().getDatabaseProductName());
        } catch (Exception e) {
            health.put("database", "DOWN");
            health.put("databaseError", e.getMessage());
        }

        return ResponseEntity.ok(health);
    }
}
