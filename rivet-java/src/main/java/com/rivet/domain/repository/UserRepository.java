package com.rivet.domain.repository;

import com.rivet.domain.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

/**
 * Repository for User entity.
 */
@Repository
public interface UserRepository extends JpaRepository<User, UUID> {

    // Find by Telegram ID
    Optional<User> findByTelegramId(Long telegramId);

    // Find by WhatsApp ID
    Optional<User> findByWhatsappId(String whatsappId);

    // Find by email
    Optional<User> findByEmail(String email);

    // Check if email exists
    boolean existsByEmail(String email);

    // Check if Telegram ID exists
    boolean existsByTelegramId(Long telegramId);

    // Find by subscription tier
    java.util.List<User> findBySubscriptionTier(User.SubscriptionTier tier);
}
