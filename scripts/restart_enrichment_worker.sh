#!/bin/bash
# Restart Enrichment Worker - AUTO-KB-005
# Usage: ./scripts/restart_enrichment_worker.sh

set -e

SERVICE_NAME="rivet-enrichment-worker"
LOG_FILE="/var/log/rivet/enrichment-worker-restart.log"

echo "$(date): Restarting $SERVICE_NAME" >> "$LOG_FILE"

# Check if running as systemd service
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "Restarting systemd service..."
    sudo systemctl restart "$SERVICE_NAME"
    sleep 2

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo "Worker restarted successfully"
        systemctl status "$SERVICE_NAME" --no-pager
        echo "$(date): Restart successful" >> "$LOG_FILE"
    else
        echo "ERROR: Worker failed to restart!"
        echo "$(date): Restart FAILED" >> "$LOG_FILE"
        exit 1
    fi
else
    # Not running as systemd, try to start manually
    echo "Service not found or not managed by systemd"
    echo "Starting worker manually..."

    # Kill any existing worker processes
    pkill -f "enrichment_worker.py" || true
    sleep 1

    # Start new worker in background
    cd /opt/rivet-pro
    source .venv/bin/activate
    nohup python -m rivet_pro.workers.enrichment_worker > /var/log/rivet/enrichment-worker.log 2>&1 &

    echo "Worker started with PID: $!"
    echo "$(date): Manual start with PID $!" >> "$LOG_FILE"
fi
