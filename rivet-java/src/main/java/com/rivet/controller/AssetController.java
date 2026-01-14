package com.rivet.controller;

import com.rivet.domain.entity.Asset;
import com.rivet.domain.entity.User;
import com.rivet.dto.request.AssetCreateRequest;
import com.rivet.dto.response.ApiResponse;
import com.rivet.security.UserPrincipal;
import com.rivet.service.AssetService;
import com.rivet.service.UserService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;
import java.util.List;
import java.util.UUID;

/**
 * Asset (Equipment) REST controller.
 * Manages equipment/assets with fuzzy matching and intelligent creation.
 */
@RestController
@RequestMapping("/api/assets")
@Api(tags = "Assets")
public class AssetController {

    @Autowired
    private AssetService assetService;

    @Autowired
    private UserService userService;

    /**
     * Get all assets with pagination.
     */
    @GetMapping
    @ApiOperation("Get all assets")
    public ResponseEntity<Page<Asset>> getAllAssets(Pageable pageable) {
        Page<Asset> assets = assetService.findAll(pageable);
        return ResponseEntity.ok(assets);
    }

    /**
     * Search assets by query.
     */
    @GetMapping("/search")
    @ApiOperation("Search assets")
    public ResponseEntity<Page<Asset>> searchAssets(
        @RequestParam String q,
        Pageable pageable
    ) {
        Page<Asset> assets = assetService.searchAssets(q, pageable);
        return ResponseEntity.ok(assets);
    }

    /**
     * Get assets by owner.
     */
    @GetMapping("/my-assets")
    @ApiOperation("Get my assets")
    public ResponseEntity<Page<Asset>> getMyAssets(
        @AuthenticationPrincipal UserPrincipal currentUser,
        Pageable pageable
    ) {
        User user = userService.findById(currentUser.getId());
        Page<Asset> assets = assetService.findByOwner(user, pageable);
        return ResponseEntity.ok(assets);
    }

    /**
     * Get asset by ID.
     */
    @GetMapping("/{id}")
    @ApiOperation("Get asset by ID")
    public ResponseEntity<Asset> getAssetById(@PathVariable UUID id) {
        Asset asset = assetService.findById(id);
        return ResponseEntity.ok(asset);
    }

    /**
     * Get asset by equipment number.
     */
    @GetMapping("/number/{equipmentNumber}")
    @ApiOperation("Get asset by equipment number")
    public ResponseEntity<Asset> getAssetByNumber(@PathVariable String equipmentNumber) {
        Asset asset = assetService.findByEquipmentNumber(equipmentNumber);
        return ResponseEntity.ok(asset);
    }

    /**
     * Create new asset.
     * Equipment number is auto-generated.
     */
    @PostMapping
    @ApiOperation("Create new asset")
    public ResponseEntity<Asset> createAsset(
        @Valid @RequestBody AssetCreateRequest request,
        @AuthenticationPrincipal UserPrincipal currentUser
    ) {
        User user = userService.findById(currentUser.getId());

        Asset asset = Asset.builder()
            .manufacturer(request.getManufacturer())
            .modelNumber(request.getModelNumber())
            .serialNumber(request.getSerialNumber())
            .equipmentType(request.getEquipmentType())
            .location(request.getLocation())
            .department(request.getDepartment())
            .criticality(request.getCriticality() != null ? request.getCriticality() : Asset.CriticalityLevel.MEDIUM)
            .description(request.getDescription())
            .installationDate(request.getInstallationDate())
            .owner(user)
            .firstReportedBy(user)
            .build();

        Asset created = assetService.createAsset(asset);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    /**
     * Match or create asset (fuzzy matching).
     * Used by Telegram bot for OCR workflow.
     */
    @PostMapping("/match-or-create")
    @ApiOperation("Match or create asset with fuzzy matching")
    public ResponseEntity<Asset> matchOrCreateAsset(
        @RequestParam String manufacturer,
        @RequestParam(required = false) String modelNumber,
        @RequestParam(required = false) String serialNumber,
        @AuthenticationPrincipal UserPrincipal currentUser
    ) {
        User user = userService.findById(currentUser.getId());
        Asset asset = assetService.matchOrCreateAsset(manufacturer, modelNumber, serialNumber, user);
        return ResponseEntity.ok(asset);
    }

    /**
     * Update asset.
     */
    @PutMapping("/{id}")
    @ApiOperation("Update asset")
    public ResponseEntity<Asset> updateAsset(
        @PathVariable UUID id,
        @RequestBody Asset assetUpdate
    ) {
        Asset updated = assetService.updateAsset(id, assetUpdate);
        return ResponseEntity.ok(updated);
    }

    /**
     * Delete asset.
     */
    @DeleteMapping("/{id}")
    @ApiOperation("Delete asset")
    public ResponseEntity<ApiResponse> deleteAsset(@PathVariable UUID id) {
        assetService.deleteAsset(id);
        return ResponseEntity.ok(new ApiResponse(true, "Asset deleted successfully"));
    }

    /**
     * Get high-maintenance assets.
     */
    @GetMapping("/high-maintenance")
    @ApiOperation("Get high-maintenance assets")
    public ResponseEntity<List<Asset>> getHighMaintenanceAssets(
        @RequestParam(defaultValue = "5") int threshold
    ) {
        List<Asset> assets = assetService.findHighMaintenanceAssets(threshold);
        return ResponseEntity.ok(assets);
    }

    /**
     * Get assets needing maintenance.
     */
    @GetMapping("/needing-maintenance")
    @ApiOperation("Get assets needing maintenance")
    public ResponseEntity<List<Asset>> getAssetsNeedingMaintenance(
        @RequestParam(defaultValue = "90") int daysSinceLastMaintenance
    ) {
        List<Asset> assets = assetService.findAssetsNeedingMaintenance(daysSinceLastMaintenance);
        return ResponseEntity.ok(assets);
    }
}
