package com.rivet.domain.entity;

import lombok.*;

import javax.persistence.*;

/**
 * Manual entity representing equipment manuals in the knowledge base.
 * Maps to Python migration 002_knowledge_base.sql (manuals table).
 */
@Entity
@Table(name = "manuals")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Manual extends AbstractAuditingEntity {

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "equipment_model_id", nullable = false)
    private EquipmentModel equipmentModel;

    @Column(name = "title", nullable = false, length = 500)
    private String title;

    @Column(name = "manual_type", length = 50)
    private String manualType;  // e.g., "user_manual", "service_manual", "parts_catalog"

    @Column(name = "file_path", length = 1000)
    private String filePath;

    @Column(name = "file_url", length = 1000)
    private String fileUrl;

    @Column(name = "page_count")
    private Integer pageCount;
}
