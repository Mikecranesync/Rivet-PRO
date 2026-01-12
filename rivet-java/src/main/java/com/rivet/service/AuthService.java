package com.rivet.service;

import com.rivet.domain.entity.User;
import com.rivet.security.JwtTokenProvider;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;

/**
 * Service for authentication operations.
 */
@Service
@Transactional
public class AuthService {

    @Autowired
    private UserService userService;

    @Autowired
    private JwtTokenProvider jwtTokenProvider;

    /**
     * Authenticate user with email and password.
     * Returns JWT token if successful.
     */
    public String authenticateUser(String email, String password) {
        if (!userService.validateCredentials(email, password)) {
            throw new IllegalArgumentException("Invalid email or password");
        }

        User user = userService.findByEmail(email);
        userService.updateLastLogin(user.getId());

        return jwtTokenProvider.generateToken(user.getId());
    }

    /**
     * Authenticate Telegram user.
     * Creates user if doesn't exist, returns JWT token.
     */
    public String authenticateTelegramUser(Long telegramId, String username) {
        User user = userService.findOrCreateByTelegramId(telegramId, username);
        userService.updateLastActive(user.getId());

        return jwtTokenProvider.generateToken(user.getId());
    }

    /**
     * Register new user and return JWT token.
     */
    public String registerUser(String email, String password, String name) {
        User user = userService.registerUser(email, password, name);
        return jwtTokenProvider.generateToken(user.getId());
    }

    /**
     * Get user from JWT token.
     */
    public User getUserFromToken(String token) {
        UUID userId = jwtTokenProvider.getUserIdFromToken(token);
        return userService.findById(userId);
    }
}
