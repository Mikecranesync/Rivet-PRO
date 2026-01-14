package com.rivet.domain.entity;

import lombok.*;

import javax.persistence.*;
import java.util.ArrayList;
import java.util.List;

/**
 * EquipmentModel entity representing canonical equipment models in the knowledge base.
 * Maps to Python migration 002_knowledge_base.sql (equipment_models table).
 */
@Entity
@Table(name = "equipment_models",
    uniqueConstraints = @UniqueConstraint(columnNames = {"manufacturer_id", "model_number"}))
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class EquipmentModel extends AbstractAuditingEntity {

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "manufacturer_id", nullable = false)
    private Manufacturer manufacturer;

    @Column(name = "model_number", nullable = false)
    private String modelNumber;

    @Column(name = "equipment_type", length = 100)
    private String equipmentType;

    @Column(name = "description", columnDefinition = "TEXT")
    private String description;

    // Relationships
    @OneToMany(mappedBy = "equipmentModel", cascade = CascadeType.ALL)
    @Builder.Default
    private List<Asset> assets = new ArrayList<>();

    @OneToMany(mappedBy = "equipmentModel", cascade = CascadeType.ALL)
    @Builder.Default
    private List<Manual> manuals = new ArrayList<>();
}
