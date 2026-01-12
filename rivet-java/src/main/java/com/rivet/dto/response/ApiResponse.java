package com.rivet.dto.response;

import lombok.AllArgsConstructor;
import lombok.Data;

/**
 * Generic API response DTO.
 */
@Data
@AllArgsConstructor
public class ApiResponse {
    private Boolean success;
    private String message;
}
