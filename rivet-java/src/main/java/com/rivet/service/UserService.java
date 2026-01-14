package com.rivet.service;

import com.rivet.domain.entity.User;
import com.rivet.domain.repository.UserRepository;
import com.rivet.exception.ResourceNotFoundException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.UUID;

/**
 * Service for User entity operations.
 */
@Service
@Transactional
public class UserService {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    /**
     * Find user by ID.
     */
    public User findById(UUID id) {
        return userRepository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("User", "id", id));
    }

    /**
     * Find user by email.
     */
    public User findByEmail(String email) {
        return userRepository.findByEmail(email)
            .orElseThrow(() -> new ResourceNotFoundException("User", "email", email));
    }

    /**
     * Find user by Telegram ID.
     */
    public User findByTelegramId(Long telegramId) {
        return userRepository.findByTelegramId(telegramId)
            .orElseThrow(() -> new ResourceNotFoundException("User", "telegramId", telegramId));
    }

    /**
     * Find or create user by Telegram ID (for Telegram bot authentication).
     */
    public User findOrCreateByTelegramId(Long telegramId, String username) {
        return userRepository.findByTelegramId(telegramId)
            .orElseGet(() -> {
                User user = User.builder()
                    .telegramId(telegramId)
                    .name(username)
                    .subscriptionTier(User.SubscriptionTier.FREE)
                    .monthlyLookupCount(0)
                    .build();
                return userRepository.save(user);
            });
    }

    /**
     * Register new user with email and password.
     */
    public User registerUser(String email, String password, String name) {
        if (userRepository.existsByEmail(email)) {
            throw new IllegalArgumentException("Email already exists");
        }

        User user = User.builder()
            .email(email)
            .passwordHash(passwordEncoder.encode(password))
            .name(name)
            .emailVerified(false)
            .subscriptionTier(User.SubscriptionTier.FREE)
            .monthlyLookupCount(0)
            .build();

        return userRepository.save(user);
    }

    /**
     * Update user's last active timestamp.
     */
    public void updateLastActive(UUID userId) {
        User user = findById(userId);
        user.setLastActiveAt(Instant.now());
        userRepository.save(user);
    }

    /**
     * Update user's last login timestamp.
     */
    public void updateLastLogin(UUID userId) {
        User user = findById(userId);
        user.setLastLoginAt(Instant.now());
        userRepository.save(user);
    }

    /**
     * Check if user exists by email.
     */
    public boolean existsByEmail(String email) {
        return userRepository.existsByEmail(email);
    }

    /**
     * Validate user credentials.
     */
    public boolean validateCredentials(String email, String rawPassword) {
        User user = userRepository.findByEmail(email).orElse(null);
        if (user == null || user.getPasswordHash() == null) {
            return false;
        }
        return passwordEncoder.matches(rawPassword, user.getPasswordHash());
    }
}
