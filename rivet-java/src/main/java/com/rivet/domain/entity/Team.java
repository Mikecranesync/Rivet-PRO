package com.rivet.domain.entity;

import lombok.*;

import javax.persistence.*;

/**
 * Team entity representing organizations for multi-user subscriptions.
 * Maps to Python migration 001_saas_layer.sql
 */
@Entity
@Table(name = "teams")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Team extends AbstractAuditingEntity {

    @Column(name = "name", nullable = false)
    private String name;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "owner_id")
    private User owner;

    @Enumerated(EnumType.STRING)
    @Column(name = "subscription_tier", nullable = false, length = 20)
    private User.SubscriptionTier subscriptionTier = User.SubscriptionTier.FREE;

    @Column(name = "max_seats")
    private Integer maxSeats = 1;
}
