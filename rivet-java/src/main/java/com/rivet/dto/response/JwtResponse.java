package com.rivet.dto.response;

import lombok.AllArgsConstructor;
import lombok.Data;

/**
 * JWT authentication response DTO.
 */
@Data
@AllArgsConstructor
public class JwtResponse {
    private String token;
    private String type = "Bearer";

    public JwtResponse(String token) {
        this.token = token;
    }
}
