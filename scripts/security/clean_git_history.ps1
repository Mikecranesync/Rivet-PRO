# =============================================================================
# RIVET Pro - Git History Cleaner (Windows PowerShell)
# Story: PHOTO-SEC-001
# Purpose: Remove .env files from git history
# =============================================================================
#
# WARNING: This script rewrites git history!
# - All collaborators must re-clone after this runs
# - Backup is created automatically
# - Run only after rotating all exposed secrets
#
# Usage: powershell -ExecutionPolicy Bypass -File scripts\security\clean_git_history.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

$RepoDir = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
$BackupDir = Join-Path (Split-Path -Parent $RepoDir) "Rivet-PRO-backup-$(Get-Date -Format 'yyyyMMdd_HHmmss')"

Write-Host "========================================"
Write-Host "RIVET Pro Git History Cleaner"
Write-Host "========================================"
Write-Host ""
Write-Host "Repository: $RepoDir"
Write-Host "Backup will be created at: $BackupDir"
Write-Host ""

# Confirmation prompt
$SecretsRotated = Read-Host "Have you rotated ALL exposed secrets? (yes/no)"
if ($SecretsRotated -ne "yes") {
    Write-Host "ERROR: Please rotate all secrets BEFORE running this script." -ForegroundColor Red
    Write-Host "See: docs\SECRETS_ROTATION_GUIDE.md"
    exit 1
}

$Confirm = Read-Host "Are you sure you want to rewrite git history? (yes/no)"
if ($Confirm -ne "yes") {
    Write-Host "Aborted."
    exit 1
}

Write-Host ""
Write-Host "Step 1: Creating backup..."
Copy-Item -Path $RepoDir -Destination $BackupDir -Recurse
Write-Host "Backup created at: $BackupDir" -ForegroundColor Green

Write-Host ""
Write-Host "Step 2: Finding .env files in history..."
Set-Location $RepoDir

# List files that will be removed
Write-Host "Files to be removed from history:"
git log --all --full-history -- "*.env" ".env*" --name-only --pretty=format: 2>$null | Sort-Object -Unique | Where-Object { $_ -ne "" }

Write-Host ""
Write-Host "Step 3: Removing .env files from history..."

# Use git filter-repo to remove .env files
# The Python path where pip installed it
$FilterRepoPath = "$env:APPDATA\Python\Python311\Scripts\git-filter-repo.exe"
if (-not (Test-Path $FilterRepoPath)) {
    # Try using python -m
    python -m git_filter_repo `
        --path .env `
        --path "rivet_pro/.env" `
        --path-glob "**/.env" `
        --path-glob "**/.env.*" `
        --path archive/ `
        --invert-paths `
        --force
} else {
    & $FilterRepoPath `
        --path .env `
        --path "rivet_pro/.env" `
        --path-glob "**/.env" `
        --path-glob "**/.env.*" `
        --path archive/ `
        --invert-paths `
        --force
}

Write-Host ""
Write-Host "Step 4: Cleaning up..."
git reflog expire --expire=now --all
git gc --prune=now --aggressive

Write-Host ""
Write-Host "========================================"
Write-Host "History cleaned successfully!" -ForegroundColor Green
Write-Host "========================================"
Write-Host ""
Write-Host "IMPORTANT NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. Force push to remote: git push origin --force --all"
Write-Host "2. Force push tags: git push origin --force --tags"
Write-Host "3. All collaborators must re-clone the repository"
Write-Host "4. Delete backup after verifying: Remove-Item -Recurse $BackupDir"
Write-Host ""
Write-Host "If something went wrong, restore from backup:"
Write-Host "  Remove-Item -Recurse $RepoDir"
Write-Host "  Rename-Item $BackupDir $RepoDir"
