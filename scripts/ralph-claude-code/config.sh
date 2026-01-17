#!/bin/bash
# Platform detection and environment configuration for Ralph
# Automatically detects Windows (Git Bash) vs Linux and sets appropriate variables

# Detect platform
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    export PLATFORM="windows"
    export PYTHON_CMD="python"
    export RALPH_MONITOR=""  # No tmux on Windows
    export WORKSPACE_ROOT="/c/Users/hharp/OneDrive/Desktop/Rivet-PRO"
else
    export PLATFORM="linux"
    export PYTHON_CMD="python3"
    export RALPH_MONITOR="--monitor"  # Use tmux on Linux
    export WORKSPACE_ROOT="$HOME/Rivet-PRO"
fi

# Navigate to workspace
cd "$WORKSPACE_ROOT" || {
    echo "ERROR: Cannot access workspace at $WORKSPACE_ROOT"
    exit 1
}

# Load environment variables from .env
if [ -f .env ]; then
    # Export all non-comment, non-empty lines
    set -a
    source <(grep -v '^#' .env | grep -v '^$')
    set +a
else
    echo "WARNING: .env file not found at $WORKSPACE_ROOT/.env"
    echo "Some features may not work without environment variables"
fi

# Verify critical environment variables
verify_env() {
    local missing=()

    if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
        missing+=("TELEGRAM_BOT_TOKEN")
    fi

    if [ -z "$DATABASE_URL" ]; then
        missing+=("DATABASE_URL")
    fi

    if [ -z "$ANTHROPIC_API_KEY" ]; then
        missing+=("ANTHROPIC_API_KEY")
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        echo "WARNING: Missing environment variables: ${missing[*]}"
        echo "Set these in .env file for full functionality"
    fi
}

# Display configuration
echo "================================================"
echo "Ralph Configuration"
echo "================================================"
echo "Platform:     $PLATFORM"
echo "Python:       $PYTHON_CMD ($($PYTHON_CMD --version 2>&1))"
echo "Workspace:    $WORKSPACE_ROOT"
echo "Monitor Mode: ${RALPH_MONITOR:-disabled}"
echo "================================================"

# Verify environment
verify_env

# Make variables available to caller
export PLATFORM PYTHON_CMD RALPH_MONITOR WORKSPACE_ROOT
