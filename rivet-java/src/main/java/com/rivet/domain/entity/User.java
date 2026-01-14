package com.rivet.domain.entity;

import lombok.*;

import javax.persistence.*;
import java.time.Instant;
import java.time.LocalDate;

/**
 * User entity representing technicians/users in the system.
 * Supports both Telegram and WhatsApp platforms.
 * Maps to Python migration 001_saas_layer.sql + 007_web_auth.sql
 */
@Entity
@Table(name = "users")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class User extends AbstractAuditingEntity {

    // Platform identifiers
    @Column(name = "telegram_id", unique = true)
    private Long telegramId;

    @Column(name = "whatsapp_id", unique = true, length = 20)
    private String whatsappId;

    // User profile
    @Column(name = "name")
    private String name;

    @Column(name = "email", unique = true)
    private String email;

    @Column(name = "company")
    private String company;

    // Web authentication (from migration 007)
    @Column(name = "password_hash")
    private String passwordHash;

    @Column(name = "email_verified")
    private Boolean emailVerified = false;

    @Column(name = "last_login_at")
    private Instant lastLoginAt;

    // Subscription
    @Enumerated(EnumType.STRING)
    @Column(name = "subscription_tier", length = 20)
    private SubscriptionTier subscriptionTier = SubscriptionTier.FREE;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "team_id")
    private Team team;

    // Usage tracking
    @Column(name = "monthly_lookup_count")
    private Integer monthlyLookupCount = 0;

    @Column(name = "lookup_count_reset_date")
    private LocalDate lookupCountResetDate;

    // Activity
    @Column(name = "last_active_at")
    private Instant lastActiveAt;

    public enum SubscriptionTier {
        FREE, PRO, TEAM
    }

    @PrePersist
    protected void onCreateUser() {
        if (lookupCountResetDate == null) {
            lookupCountResetDate = LocalDate.now();
        }
        if (lastActiveAt == null) {
            lastActiveAt = Instant.now();
        }
    }
}
