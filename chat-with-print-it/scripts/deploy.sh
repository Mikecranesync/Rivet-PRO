#!/bin/bash
# Deploy Chat with Print-it to VPS

set -e

VPS_IP="72.60.175.144"
VPS_USER="root"
REMOTE_DIR="/opt/rivet-pro/chat-with-print-it"

echo "🚀 Deploying Chat with Print-it..."

# Create remote directory
ssh $VPS_USER@$VPS_IP "mkdir -p $REMOTE_DIR/{n8n-workflows,database,landing-page,scripts}"

# Copy files
echo "📦 Copying files..."
scp -r n8n-workflows/* $VPS_USER@$VPS_IP:$REMOTE_DIR/n8n-workflows/
scp -r database/* $VPS_USER@$VPS_IP:$REMOTE_DIR/database/
scp -r landing-page/* $VPS_USER@$VPS_IP:$REMOTE_DIR/landing-page/
scp .env.example $VPS_USER@$VPS_IP:$REMOTE_DIR/

# Run database migration
echo "🗄️ Running database migration..."
ssh $VPS_USER@$VPS_IP "cd $REMOTE_DIR && psql \$DATABASE_URL -f database/schema.sql"

# Setup nginx for landing page
echo "🌐 Setting up nginx..."
ssh $VPS_USER@$VPS_IP "cp $REMOTE_DIR/landing-page/index.html /var/www/html/rivetpro/"

# Import workflows to n8n
echo "📊 Import workflows manually via n8n UI at http://$VPS_IP:5678"

echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env and fill in your values"
echo "2. Import n8n workflows via the UI"
echo "3. Configure Telegram webhook"
echo "4. Setup Stripe webhook to point to your n8n URL"
