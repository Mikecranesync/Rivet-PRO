package com.rivet.dto.request;

import com.rivet.domain.entity.WorkOrder;
import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import java.util.UUID;

/**
 * Work order creation request DTO.
 */
@Data
public class WorkOrderCreateRequest {

    @NotNull(message = "Equipment ID is required")
    private UUID equipmentId;

    @NotBlank(message = "Title is required")
    private String title;

    @NotBlank(message = "Description is required")
    private String description;

    private WorkOrder.PriorityLevel priority;
    private WorkOrder.SourceType source;
    private String[] faultCodes;
    private String[] symptoms;
}
