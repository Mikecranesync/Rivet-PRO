package com.rivet.domain.repository;

import com.rivet.domain.entity.Asset;
import com.rivet.domain.entity.User;
import com.rivet.domain.entity.WorkOrder;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Repository for WorkOrder entity.
 */
@Repository
public interface WorkOrderRepository extends JpaRepository<WorkOrder, UUID> {

    // Find by work order number
    Optional<WorkOrder> findByWorkOrderNumber(String workOrderNumber);

    // Find by user
    Page<WorkOrder> findByUser(User user, Pageable pageable);
    List<WorkOrder> findByUserOrderByCreatedAtDesc(User user);

    // Find by equipment
    Page<WorkOrder> findByEquipment(Asset equipment, Pageable pageable);
    List<WorkOrder> findByEquipmentOrderByCreatedAtDesc(Asset equipment);

    // Find by status
    Page<WorkOrder> findByStatus(WorkOrder.WorkOrderStatus status, Pageable pageable);
    List<WorkOrder> findByStatus(WorkOrder.WorkOrderStatus status);

    // Find by priority
    List<WorkOrder> findByPriority(WorkOrder.PriorityLevel priority);

    // Find by user and status
    Page<WorkOrder> findByUserAndStatus(User user, WorkOrder.WorkOrderStatus status, Pageable pageable);

    // Find by equipment and status
    List<WorkOrder> findByEquipmentAndStatus(Asset equipment, WorkOrder.WorkOrderStatus status);

    // Find open work orders
    @Query("SELECT wo FROM WorkOrder wo WHERE wo.status = 'OPEN' ORDER BY wo.priority DESC, wo.createdAt ASC")
    List<WorkOrder> findOpenWorkOrders();

    // Find work orders by date range
    @Query("SELECT wo FROM WorkOrder wo WHERE wo.createdAt BETWEEN :startDate AND :endDate")
    List<WorkOrder> findByDateRange(
        @Param("startDate") Instant startDate,
        @Param("endDate") Instant endDate
    );

    // Count work orders by status
    long countByStatus(WorkOrder.WorkOrderStatus status);

    // Count work orders by user
    long countByUser(User user);

    // Count work orders by equipment
    long countByEquipment(Asset equipment);

    // Find recent work orders
    Page<WorkOrder> findAllByOrderByCreatedAtDesc(Pageable pageable);

    // Search work orders
    @Query("SELECT wo FROM WorkOrder wo WHERE " +
           "LOWER(wo.title) LIKE LOWER(CONCAT('%', :search, '%')) OR " +
           "LOWER(wo.description) LIKE LOWER(CONCAT('%', :search, '%')) OR " +
           "LOWER(wo.workOrderNumber) LIKE LOWER(CONCAT('%', :search, '%'))")
    Page<WorkOrder> searchWorkOrders(@Param("search") String search, Pageable pageable);

    // Find high priority incomplete work orders
    @Query("SELECT wo FROM WorkOrder wo WHERE " +
           "wo.status IN ('OPEN', 'IN_PROGRESS') AND " +
           "wo.priority IN ('HIGH', 'CRITICAL') " +
           "ORDER BY wo.priority DESC, wo.createdAt ASC")
    List<WorkOrder> findHighPriorityIncomplete();
}
