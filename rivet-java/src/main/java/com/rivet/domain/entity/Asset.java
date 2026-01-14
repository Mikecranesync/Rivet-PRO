package com.rivet.domain.entity;

import lombok.*;

import javax.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

/**
 * Asset entity representing equipment/machinery instances.
 * Maps to Python migration 003_cmms_equipment.sql (cmms_equipment table).
 * Extends this with Grashjs Asset model features.
 */
@Entity
@Table(name = "cmms_equipment")  // Keep Python table name for compatibility
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Asset extends AbstractAuditingEntity {

    // Equipment identification
    @Column(name = "equipment_number", unique = true, nullable = false, length = 50)
    private String equipmentNumber;  // Auto-generated: EQ-2025-0001

    // Links to knowledge base
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "equipment_model_id")
    private EquipmentModel equipmentModel;

    // Equipment details (denormalized for performance)
    @Column(name = "manufacturer", nullable = false)
    private String manufacturer;

    @Column(name = "model_number")
    private String modelNumber;

    @Column(name = "serial_number")
    private String serialNumber;

    @Column(name = "equipment_type", length = 100)
    private String equipmentType;

    // Location & context
    @Column(name = "location", length = 500)
    private String location;

    @Column(name = "department")
    private String department;

    @Enumerated(EnumType.STRING)
    @Column(name = "criticality", columnDefinition = "criticality_level")
    private CriticalityLevel criticality = CriticalityLevel.MEDIUM;

    // Ownership
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "owned_by_user_id")
    private User owner;

    @Column(name = "machine_id")
    private java.util.UUID machineId;  // Link to user_machines table

    // Metadata
    @Column(name = "description", columnDefinition = "TEXT")
    private String description;

    @Column(name = "photo_file_id", length = 500)
    private String photoFileId;  // Telegram file ID

    @Column(name = "installation_date")
    private LocalDate installationDate;

    @Column(name = "last_maintenance_date")
    private LocalDate lastMaintenanceDate;

    // Statistics (updated by triggers)
    @Column(name = "work_order_count")
    private Integer workOrderCount = 0;

    @Column(name = "total_downtime_hours")
    private Float totalDowntimeHours = 0.0f;

    @Column(name = "last_reported_fault", length = 100)
    private String lastReportedFault;

    @Column(name = "last_work_order_at")
    private Instant lastWorkOrderAt;

    // Reporter
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "first_reported_by")
    private User firstReportedBy;

    // Grashjs extensions (will be added in migration 003-asset-extensions.xml)
    // Uncommenting these for future compatibility
    /*
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "location_id")
    private Location locationEntity;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "parent_asset_id")
    private Asset parentAsset;

    @OneToMany(mappedBy = "parentAsset", cascade = CascadeType.ALL)
    private List<Asset> children = new ArrayList<>();

    @Column(name = "acquisition_cost", precision = 10, scale = 2)
    private BigDecimal acquisitionCost;

    @Column(name = "warranty_expiration_date")
    private LocalDate warrantyExpirationDate;

    @Enumerated(EnumType.STRING)
    @Column(name = "status")
    private AssetStatus status = AssetStatus.OPERATIONAL;
    */

    // Relationships
    @OneToMany(mappedBy = "equipment", cascade = CascadeType.ALL)
    @Builder.Default
    private List<WorkOrder> workOrders = new ArrayList<>();

    public enum CriticalityLevel {
        LOW, MEDIUM, HIGH, CRITICAL
    }

    public enum AssetStatus {
        OPERATIONAL, DOWN, MAINTENANCE, DECOMMISSIONED
    }

    // Helper method to add work order
    public void addWorkOrder(WorkOrder workOrder) {
        workOrders.add(workOrder);
        workOrder.setEquipment(this);
    }
}
