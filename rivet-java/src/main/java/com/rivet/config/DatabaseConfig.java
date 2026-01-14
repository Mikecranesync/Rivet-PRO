package com.rivet.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.transaction.annotation.EnableTransactionManagement;

/**
 * Database configuration for JPA and transaction management.
 */
@Configuration
@EnableJpaRepositories(basePackages = "com.rivet.domain.repository")
@EnableJpaAuditing
@EnableTransactionManagement
public class DatabaseConfig {
    // Configuration handled by application.properties and Spring Boot auto-configuration
}
