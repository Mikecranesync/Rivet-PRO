package com.rivet.domain.entity;

import lombok.*;
import org.hibernate.annotations.Type;

import javax.persistence.*;
import java.util.ArrayList;
import java.util.List;

/**
 * Manufacturer entity representing equipment manufacturers.
 * Maps to Python migration 002_knowledge_base.sql (manufacturers table).
 */
@Entity
@Table(name = "manufacturers")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Manufacturer extends AbstractAuditingEntity {

    @Column(name = "name", nullable = false, unique = true)
    private String name;

    @Type(type = "string-array")
    @Column(name = "aliases", columnDefinition = "text[]")
    private String[] aliases;

    // Relationships
    @OneToMany(mappedBy = "manufacturer", cascade = CascadeType.ALL)
    @Builder.Default
    private List<EquipmentModel> equipmentModels = new ArrayList<>();
}
