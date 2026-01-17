#!/bin/bash
# =============================================================================
# RIVET Pro - Git History Cleaner
# Story: PHOTO-SEC-001
# Purpose: Remove .env files from git history
# =============================================================================
#
# WARNING: This script rewrites git history!
# - All collaborators must re-clone after this runs
# - Backup is created automatically
# - Run only after rotating all exposed secrets
#
# Usage: bash scripts/security/clean_git_history.sh
# =============================================================================

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP_DIR="${REPO_DIR}/../Rivet-PRO-backup-$(date +%Y%m%d_%H%M%S)"

echo "========================================"
echo "RIVET Pro Git History Cleaner"
echo "========================================"
echo ""
echo "Repository: ${REPO_DIR}"
echo "Backup will be created at: ${BACKUP_DIR}"
echo ""

# Confirmation prompt
read -p "Have you rotated ALL exposed secrets? (yes/no): " SECRETS_ROTATED
if [ "$SECRETS_ROTATED" != "yes" ]; then
    echo "ERROR: Please rotate all secrets BEFORE running this script."
    echo "See: docs/SECRETS_ROTATION_GUIDE.md"
    exit 1
fi

read -p "Are you sure you want to rewrite git history? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "Step 1: Creating backup..."
cp -r "${REPO_DIR}" "${BACKUP_DIR}"
echo "Backup created at: ${BACKUP_DIR}"

echo ""
echo "Step 2: Finding .env files in history..."
cd "${REPO_DIR}"

# List files that will be removed
echo "Files to be removed from history:"
git log --all --full-history -- "*.env" --name-only --pretty=format: | sort -u | grep -v '^$' || echo "(none found with *.env pattern)"
git log --all --full-history -- ".env*" --name-only --pretty=format: | sort -u | grep -v '^$' || echo "(none found with .env* pattern)"

echo ""
echo "Step 3: Removing .env files from history..."

# Use git filter-repo to remove .env files
# Note: This removes ALL files matching these patterns from ALL history
python -m git_filter_repo \
    --path .env --path-glob '**/.env' --path-glob '*.env' \
    --path rivet_pro/.env \
    --path archive/ \
    --invert-paths \
    --force

echo ""
echo "Step 4: Cleaning up..."
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo ""
echo "========================================"
echo "History cleaned successfully!"
echo "========================================"
echo ""
echo "IMPORTANT NEXT STEPS:"
echo "1. Force push to remote: git push origin --force --all"
echo "2. Force push tags: git push origin --force --tags"
echo "3. All collaborators must re-clone the repository"
echo "4. Delete backup after verifying: rm -rf ${BACKUP_DIR}"
echo ""
echo "If something went wrong, restore from backup:"
echo "  rm -rf ${REPO_DIR}"
echo "  mv ${BACKUP_DIR} ${REPO_DIR}"
