package com.rivet.dto.request;

import com.rivet.domain.entity.Asset;
import lombok.Data;

import javax.validation.constraints.NotBlank;
import java.time.LocalDate;

/**
 * Asset creation request DTO.
 */
@Data
public class AssetCreateRequest {

    @NotBlank(message = "Manufacturer is required")
    private String manufacturer;

    private String modelNumber;
    private String serialNumber;
    private String equipmentType;
    private String location;
    private String department;
    private Asset.CriticalityLevel criticality;
    private String description;
    private LocalDate installationDate;
}
