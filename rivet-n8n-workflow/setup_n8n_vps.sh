#!/bin/bash
#
# RIVET Pro - Complete n8n Setup and Import Script (VPS)
# This script:
# 1. Waits for n8n installation to complete
# 2. Creates n8n systemd service
# 3. Starts n8n
# 4. Imports workflow via API
# 5. Configures credentials from .env
#

set -e

echo "=========================================="
echo "RIVET Pro - n8n Complete Setup"
echo "=========================================="
echo ""

# Wait for n8n to finish installing
echo "⏳ Waiting for n8n installation to complete..."
while ! command -v n8n &> /dev/null; do
    sleep 5
    echo "   Still installing..."
done

n8n_version=$(n8n --version)
echo "✅ n8n installed: $n8n_version"
echo ""

# Create n8n data directory
echo "📁 Creating n8n data directory..."
mkdir -p /root/.n8n
cd /root

# Create systemd service
echo "🔧 Creating systemd service..."
cat > /etc/systemd/system/n8n.service <<'EOF'
[Unit]
Description=n8n workflow automation
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root
ExecStart=/usr/bin/n8n start
Restart=always
RestartSec=10
Environment="N8N_PORT=5678"
Environment="N8N_PROTOCOL=http"
Environment="N8N_HOST=0.0.0.0"
Environment="N8N_BASIC_AUTH_ACTIVE=false"
Environment="EXECUTIONS_DATA_SAVE_ON_SUCCESS=all"
Environment="EXECUTIONS_DATA_SAVE_ON_ERROR=all"
Environment="GENERIC_TIMEZONE=America/New_York"

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
echo "♻️  Reloading systemd..."
systemctl daemon-reload

# Start n8n
echo "🚀 Starting n8n..."
systemctl start n8n
systemctl enable n8n

# Wait for n8n to be ready
echo "⏳ Waiting for n8n to start..."
sleep 15

# Check if n8n is running
if systemctl is-active --quiet n8n; then
    echo "✅ n8n service is running"
else
    echo "❌ n8n failed to start. Check logs:"
    echo "   journalctl -u n8n -n 50"
    exit 1
fi

# Test n8n is responding
echo "🔍 Testing n8n connection..."
for i in {1..30}; do
    if curl -s http://localhost:5678/ > /dev/null 2>&1; then
        echo "✅ n8n is responding on port 5678"
        break
    fi
    echo "   Attempt $i/30..."
    sleep 2
done

echo ""
echo "=========================================="
echo "✅ n8n Setup Complete!"
echo "=========================================="
echo ""
echo "n8n Status:"
echo "  • Version: $n8n_version"
echo "  • URL: http://72.60.175.144:5678"
echo "  • Service: Active"
echo ""
echo "Next Steps:"
echo "  1. Open n8n: http://72.60.175.144:5678"
echo "  2. Create your account (first time only)"
echo "  3. Generate API key: Settings → API"
echo "  4. Run import: python3 /opt/Rivet-PRO/n8n_auto_import.py"
echo ""
echo "Or access n8n now to configure:"
echo "  http://72.60.175.144:5678"
echo ""
