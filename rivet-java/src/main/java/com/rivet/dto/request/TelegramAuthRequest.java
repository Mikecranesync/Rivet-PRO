package com.rivet.dto.request;

import lombok.Data;

import javax.validation.constraints.NotNull;

/**
 * Telegram authentication request DTO.
 */
@Data
public class TelegramAuthRequest {

    @NotNull(message = "Telegram user ID is required")
    private Long telegramUserId;

    private String username;
}
