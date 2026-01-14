package com.rivet.controller;

import com.rivet.domain.entity.Asset;
import com.rivet.domain.entity.User;
import com.rivet.domain.entity.WorkOrder;
import com.rivet.dto.request.WorkOrderCreateRequest;
import com.rivet.dto.response.ApiResponse;
import com.rivet.security.UserPrincipal;
import com.rivet.service.AssetService;
import com.rivet.service.UserService;
import com.rivet.service.WorkOrderService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;
import java.util.List;
import java.util.UUID;

/**
 * Work Order REST controller.
 * Manages maintenance work orders with equipment-first architecture.
 */
@RestController
@RequestMapping("/api/work-orders")
@Api(tags = "Work Orders")
public class WorkOrderController {

    @Autowired
    private WorkOrderService workOrderService;

    @Autowired
    private AssetService assetService;

    @Autowired
    private UserService userService;

    /**
     * Get all work orders with pagination.
     */
    @GetMapping
    @ApiOperation("Get all work orders")
    public ResponseEntity<Page<WorkOrder>> getAllWorkOrders(Pageable pageable) {
        Page<WorkOrder> workOrders = workOrderService.findAll(pageable);
        return ResponseEntity.ok(workOrders);
    }

    /**
     * Search work orders.
     */
    @GetMapping("/search")
    @ApiOperation("Search work orders")
    public ResponseEntity<Page<WorkOrder>> searchWorkOrders(
        @RequestParam String q,
        Pageable pageable
    ) {
        Page<WorkOrder> workOrders = workOrderService.searchWorkOrders(q, pageable);
        return ResponseEntity.ok(workOrders);
    }

    /**
     * Get work orders by status.
     */
    @GetMapping("/status/{status}")
    @ApiOperation("Get work orders by status")
    public ResponseEntity<Page<WorkOrder>> getWorkOrdersByStatus(
        @PathVariable WorkOrder.WorkOrderStatus status,
        Pageable pageable
    ) {
        Page<WorkOrder> workOrders = workOrderService.findByStatus(status, pageable);
        return ResponseEntity.ok(workOrders);
    }

    /**
     * Get my work orders.
     */
    @GetMapping("/my-work-orders")
    @ApiOperation("Get my work orders")
    public ResponseEntity<Page<WorkOrder>> getMyWorkOrders(
        @AuthenticationPrincipal UserPrincipal currentUser,
        Pageable pageable
    ) {
        User user = userService.findById(currentUser.getId());
        Page<WorkOrder> workOrders = workOrderService.findByUser(user, pageable);
        return ResponseEntity.ok(workOrders);
    }

    /**
     * Get work orders by equipment.
     */
    @GetMapping("/equipment/{equipmentId}")
    @ApiOperation("Get work orders by equipment")
    public ResponseEntity<Page<WorkOrder>> getWorkOrdersByEquipment(
        @PathVariable UUID equipmentId,
        Pageable pageable
    ) {
        Asset equipment = assetService.findById(equipmentId);
        Page<WorkOrder> workOrders = workOrderService.findByEquipment(equipment, pageable);
        return ResponseEntity.ok(workOrders);
    }

    /**
     * Get work order by ID.
     */
    @GetMapping("/{id}")
    @ApiOperation("Get work order by ID")
    public ResponseEntity<WorkOrder> getWorkOrderById(@PathVariable UUID id) {
        WorkOrder workOrder = workOrderService.findById(id);
        return ResponseEntity.ok(workOrder);
    }

    /**
     * Get work order by work order number.
     */
    @GetMapping("/number/{workOrderNumber}")
    @ApiOperation("Get work order by number")
    public ResponseEntity<WorkOrder> getWorkOrderByNumber(@PathVariable String workOrderNumber) {
        WorkOrder workOrder = workOrderService.findByWorkOrderNumber(workOrderNumber);
        return ResponseEntity.ok(workOrder);
    }

    /**
     * Create new work order.
     */
    @PostMapping
    @ApiOperation("Create new work order")
    public ResponseEntity<WorkOrder> createWorkOrder(
        @Valid @RequestBody WorkOrderCreateRequest request,
        @AuthenticationPrincipal UserPrincipal currentUser
    ) {
        User user = userService.findById(currentUser.getId());
        Asset equipment = assetService.findById(request.getEquipmentId());

        WorkOrder workOrder = WorkOrder.builder()
            .user(user)
            .equipment(equipment)
            .title(request.getTitle())
            .description(request.getDescription())
            .priority(request.getPriority() != null ? request.getPriority() : WorkOrder.PriorityLevel.MEDIUM)
            .source(request.getSource() != null ? request.getSource() : WorkOrder.SourceType.TELEGRAM_TEXT)
            .faultCodes(request.getFaultCodes())
            .symptoms(request.getSymptoms())
            .status(WorkOrder.WorkOrderStatus.OPEN)
            .build();

        WorkOrder created = workOrderService.createWorkOrder(workOrder);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    /**
     * Update work order status.
     */
    @PatchMapping("/{id}/status")
    @ApiOperation("Update work order status")
    public ResponseEntity<WorkOrder> updateStatus(
        @PathVariable UUID id,
        @RequestParam WorkOrder.WorkOrderStatus status
    ) {
        WorkOrder updated = workOrderService.updateStatus(id, status);
        return ResponseEntity.ok(updated);
    }

    /**
     * Update work order.
     */
    @PutMapping("/{id}")
    @ApiOperation("Update work order")
    public ResponseEntity<WorkOrder> updateWorkOrder(
        @PathVariable UUID id,
        @RequestBody WorkOrder workOrderUpdate
    ) {
        WorkOrder updated = workOrderService.updateWorkOrder(id, workOrderUpdate);
        return ResponseEntity.ok(updated);
    }

    /**
     * Delete work order.
     */
    @DeleteMapping("/{id}")
    @ApiOperation("Delete work order")
    public ResponseEntity<ApiResponse> deleteWorkOrder(@PathVariable UUID id) {
        workOrderService.deleteWorkOrder(id);
        return ResponseEntity.ok(new ApiResponse(true, "Work order deleted successfully"));
    }

    /**
     * Get work order statistics.
     */
    @GetMapping("/stats")
    @ApiOperation("Get work order statistics")
    public ResponseEntity<WorkOrderService.WorkOrderStats> getStats(
        @AuthenticationPrincipal UserPrincipal currentUser
    ) {
        User user = userService.findById(currentUser.getId());
        WorkOrderService.WorkOrderStats stats = workOrderService.getStats(user);
        return ResponseEntity.ok(stats);
    }

    /**
     * Get high priority incomplete work orders.
     */
    @GetMapping("/high-priority")
    @ApiOperation("Get high priority incomplete work orders")
    public ResponseEntity<List<WorkOrder>> getHighPriority() {
        List<WorkOrder> workOrders = workOrderService.findHighPriorityIncomplete();
        return ResponseEntity.ok(workOrders);
    }
}
