package com.rivet.domain.repository;

import com.rivet.domain.entity.Asset;
import com.rivet.domain.entity.User;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Repository for Asset (Equipment) entity.
 */
@Repository
public interface AssetRepository extends JpaRepository<Asset, UUID> {

    // Find by equipment number
    Optional<Asset> findByEquipmentNumber(String equipmentNumber);

    // Find by serial number
    Optional<Asset> findBySerialNumber(String serialNumber);

    // Find by owner
    List<Asset> findByOwner(User owner);
    Page<Asset> findByOwner(User owner, Pageable pageable);

    // Find by manufacturer
    Page<Asset> findByManufacturerContainingIgnoreCase(String manufacturer, Pageable pageable);

    // Find by location
    Page<Asset> findByLocationContainingIgnoreCase(String location, Pageable pageable);

    // Find by criticality
    List<Asset> findByCriticality(Asset.CriticalityLevel criticality);

    // Search across multiple fields
    @Query("SELECT a FROM Asset a WHERE " +
           "LOWER(a.manufacturer) LIKE LOWER(CONCAT('%', :search, '%')) OR " +
           "LOWER(a.modelNumber) LIKE LOWER(CONCAT('%', :search, '%')) OR " +
           "LOWER(a.serialNumber) LIKE LOWER(CONCAT('%', :search, '%')) OR " +
           "LOWER(a.equipmentNumber) LIKE LOWER(CONCAT('%', :search, '%')) OR " +
           "LOWER(a.location) LIKE LOWER(CONCAT('%', :search, '%'))")
    Page<Asset> searchAssets(@Param("search") String search, Pageable pageable);

    // Find assets with work order count above threshold
    @Query("SELECT a FROM Asset a WHERE a.workOrderCount >= :threshold ORDER BY a.workOrderCount DESC")
    List<Asset> findHighMaintenanceAssets(@Param("threshold") int threshold);

    // Find assets needing maintenance (based on last maintenance date)
    @Query("SELECT a FROM Asset a WHERE a.lastMaintenanceDate IS NULL OR " +
           "a.lastMaintenanceDate < CURRENT_DATE - :daysSinceLastMaintenance")
    List<Asset> findAssetsNeedingMaintenance(@Param("daysSinceLastMaintenance") int days);

    // Fuzzy matching for manufacturer and model
    @Query("SELECT a FROM Asset a WHERE " +
           "LOWER(a.manufacturer) = LOWER(:manufacturer) AND " +
           "LOWER(a.modelNumber) = LOWER(:modelNumber)")
    List<Asset> findByManufacturerAndModel(
        @Param("manufacturer") String manufacturer,
        @Param("modelNumber") String modelNumber
    );
}
