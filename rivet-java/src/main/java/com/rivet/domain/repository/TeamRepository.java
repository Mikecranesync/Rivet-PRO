package com.rivet.domain.repository;

import com.rivet.domain.entity.Team;
import com.rivet.domain.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

/**
 * Repository for Team entity.
 */
@Repository
public interface TeamRepository extends JpaRepository<Team, UUID> {

    // Find by owner
    List<Team> findByOwner(User owner);

    // Find by name
    List<Team> findByNameContainingIgnoreCase(String name);
}
