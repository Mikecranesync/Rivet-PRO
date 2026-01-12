package com.rivet.domain.entity;

import lombok.*;
import org.hibernate.annotations.Type;

import javax.persistence.*;
import java.time.Instant;
import java.util.UUID;

/**
 * WorkOrder entity representing maintenance work orders.
 * Maps to Python migration 004_work_orders.sql
 */
@Entity
@Table(name = "work_orders")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class WorkOrder extends AbstractAuditingEntity {

    // Work order identification
    @Column(name = "work_order_number", unique = true, nullable = false, length = 50)
    private String workOrderNumber;  // Auto-generated: WO-2025-0001

    // User & Source
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(name = "telegram_username")
    private String telegramUsername;

    @Column(name = "created_by_agent", length = 100)
    private String createdByAgent;  // siemens_agent, rockwell_agent, etc.

    @Enumerated(EnumType.STRING)
    @Column(name = "source", nullable = false, columnDefinition = "source_type")
    private SourceType source;

    // Equipment (REQUIRED - equipment-first architecture)
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "equipment_id", nullable = false)
    private Asset equipment;

    // Denormalized equipment details (for performance)
    @Column(name = "equipment_number", length = 50)
    private String equipmentNumber;

    @Column(name = "manufacturer")
    private String manufacturer;

    @Column(name = "model_number")
    private String modelNumber;

    @Column(name = "serial_number")
    private String serialNumber;

    @Column(name = "equipment_type", length = 100)
    private String equipmentType;

    @Column(name = "machine_id")
    private UUID machineId;

    @Column(name = "location", length = 500)
    private String location;

    // Issue details
    @Column(name = "title", nullable = false, length = 500)
    private String title;

    @Column(name = "description", nullable = false, columnDefinition = "TEXT")
    private String description;

    @Type(type = "string-array")
    @Column(name = "fault_codes", columnDefinition = "text[]")
    private String[] faultCodes;

    @Type(type = "string-array")
    @Column(name = "symptoms", columnDefinition = "text[]")
    private String[] symptoms;

    // Response metadata
    @Column(name = "answer_text", columnDefinition = "TEXT")
    private String answerText;

    @Column(name = "confidence_score")
    private Float confidenceScore;

    @Enumerated(EnumType.STRING)
    @Column(name = "route_taken", columnDefinition = "route_type")
    private RouteType routeTaken;

    @Type(type = "string-array")
    @Column(name = "suggested_actions", columnDefinition = "text[]")
    private String[] suggestedActions;

    @Type(type = "string-array")
    @Column(name = "safety_warnings", columnDefinition = "text[]")
    private String[] safetyWarnings;

    @Type(type = "string-array")
    @Column(name = "cited_kb_atoms", columnDefinition = "text[]")
    private String[] citedKbAtoms;

    @Type(type = "string-array")
    @Column(name = "manual_links", columnDefinition = "text[]")
    private String[] manualLinks;

    // Status & Priority
    @Enumerated(EnumType.STRING)
    @Column(name = "status", columnDefinition = "work_order_status")
    private WorkOrderStatus status = WorkOrderStatus.OPEN;

    @Enumerated(EnumType.STRING)
    @Column(name = "priority", columnDefinition = "priority_level")
    private PriorityLevel priority = PriorityLevel.MEDIUM;

    // Audit trail
    @Column(name = "trace_id")
    private UUID traceId;

    @Column(name = "conversation_id")
    private UUID conversationId;

    @Column(name = "research_triggered")
    private Boolean researchTriggered = false;

    @Column(name = "enrichment_triggered")
    private Boolean enrichmentTriggered = false;

    @Column(name = "completed_at")
    private Instant completedAt;

    // Enums matching Python migrations
    public enum SourceType {
        TELEGRAM_TEXT, TELEGRAM_VOICE, TELEGRAM_PHOTO,
        TELEGRAM_PRINT_QA, TELEGRAM_MANUAL_GAP,
        WHATSAPP_TEXT, WHATSAPP_VOICE, WHATSAPP_PHOTO
    }

    public enum RouteType {
        A, B, C, D  // A=KB, B=SME, C=Research, D=Clarification
    }

    public enum WorkOrderStatus {
        OPEN, IN_PROGRESS, COMPLETED, CANCELLED
    }

    public enum PriorityLevel {
        LOW, MEDIUM, HIGH, CRITICAL
    }

    // Helper methods
    public void markAsCompleted() {
        this.status = WorkOrderStatus.COMPLETED;
        this.completedAt = Instant.now();
    }

    public void markAsInProgress() {
        this.status = WorkOrderStatus.IN_PROGRESS;
    }

    public void markAsCancelled() {
        this.status = WorkOrderStatus.CANCELLED;
    }
}
