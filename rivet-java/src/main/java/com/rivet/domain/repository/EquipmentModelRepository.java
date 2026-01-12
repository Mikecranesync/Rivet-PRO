package com.rivet.domain.repository;

import com.rivet.domain.entity.EquipmentModel;
import com.rivet.domain.entity.Manufacturer;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Repository for EquipmentModel entity.
 */
@Repository
public interface EquipmentModelRepository extends JpaRepository<EquipmentModel, UUID> {

    // Find by manufacturer and model number
    Optional<EquipmentModel> findByManufacturerAndModelNumber(
        Manufacturer manufacturer,
        String modelNumber
    );

    // Find by manufacturer
    List<EquipmentModel> findByManufacturer(Manufacturer manufacturer);

    // Find by equipment type
    List<EquipmentModel> findByEquipmentType(String equipmentType);

    // Search by model number
    List<EquipmentModel> findByModelNumberContainingIgnoreCase(String modelNumber);
}
