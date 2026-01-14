package com.rivet.controller;

import com.rivet.domain.entity.User;
import com.rivet.dto.request.LoginRequest;
import com.rivet.dto.request.RegisterRequest;
import com.rivet.dto.request.TelegramAuthRequest;
import com.rivet.dto.response.ApiResponse;
import com.rivet.dto.response.JwtResponse;
import com.rivet.security.UserPrincipal;
import com.rivet.service.AuthService;
import com.rivet.service.UserService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;

/**
 * Authentication REST controller.
 * Handles user registration, login, and Telegram authentication.
 */
@RestController
@RequestMapping("/api/auth")
@Api(tags = "Authentication")
public class AuthController {

    @Autowired
    private AuthService authService;

    @Autowired
    private UserService userService;

    /**
     * Register new user with email and password.
     */
    @PostMapping("/register")
    @ApiOperation("Register new user")
    public ResponseEntity<JwtResponse> register(@Valid @RequestBody RegisterRequest request) {
        String token = authService.registerUser(
            request.getEmail(),
            request.getPassword(),
            request.getName()
        );
        return ResponseEntity.ok(new JwtResponse(token));
    }

    /**
     * Login with email and password.
     */
    @PostMapping("/login")
    @ApiOperation("Login with email and password")
    public ResponseEntity<JwtResponse> login(@Valid @RequestBody LoginRequest request) {
        String token = authService.authenticateUser(request.getEmail(), request.getPassword());
        return ResponseEntity.ok(new JwtResponse(token));
    }

    /**
     * Authenticate Telegram user.
     * Creates user if doesn't exist.
     */
    @PostMapping("/telegram")
    @ApiOperation("Authenticate Telegram user")
    public ResponseEntity<JwtResponse> authenticateTelegram(@Valid @RequestBody TelegramAuthRequest request) {
        String token = authService.authenticateTelegramUser(
            request.getTelegramUserId(),
            request.getUsername()
        );
        return ResponseEntity.ok(new JwtResponse(token));
    }

    /**
     * Get current authenticated user.
     */
    @GetMapping("/me")
    @ApiOperation("Get current user")
    public ResponseEntity<User> getCurrentUser(@AuthenticationPrincipal UserPrincipal currentUser) {
        User user = userService.findById(currentUser.getId());
        return ResponseEntity.ok(user);
    }

    /**
     * Check if email is available.
     */
    @GetMapping("/check-email")
    @ApiOperation("Check if email is available")
    public ResponseEntity<ApiResponse> checkEmail(@RequestParam String email) {
        boolean exists = userService.existsByEmail(email);
        return ResponseEntity.ok(new ApiResponse(!exists, exists ? "Email already exists" : "Email available"));
    }
}
