package com.rivet.domain.repository;

import com.rivet.domain.entity.Manufacturer;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

/**
 * Repository for Manufacturer entity.
 */
@Repository
public interface ManufacturerRepository extends JpaRepository<Manufacturer, UUID> {

    // Find by name
    Optional<Manufacturer> findByNameIgnoreCase(String name);

    // Find by name or alias
    @Query("SELECT m FROM Manufacturer m WHERE " +
           "LOWER(m.name) = LOWER(:name) OR " +
           ":name = ANY(SELECT LOWER(alias) FROM unnest(m.aliases) AS alias)")
    Optional<Manufacturer> findByNameOrAlias(@Param("name") String name);
}
