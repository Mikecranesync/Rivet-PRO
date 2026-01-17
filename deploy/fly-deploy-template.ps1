# Fly.io Deployment Script for RIVET Pro Telegram Bot
# Run this in PowerShell after installing Fly CLI
#
# Prerequisites:
#   1. Install Fly CLI: iwr https://fly.io/install.ps1 -useb | iex
#   2. Login: fly auth login
#   3. Copy this to fly-deploy.ps1 and fill in your secrets
#   4. Run: .\deploy\fly-deploy.ps1

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RIVET Pro - Fly.io Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# App name from fly.toml
$APP_NAME = "rivet-cmms-bot"

# Check if fly is installed
try {
    $flyVersion = fly version 2>&1
    Write-Host "[OK] Fly CLI installed: $flyVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Fly CLI not found. Install with:" -ForegroundColor Red
    Write-Host "  iwr https://fly.io/install.ps1 -useb | iex" -ForegroundColor Yellow
    exit 1
}

# Check if authenticated
try {
    $whoami = fly auth whoami 2>&1
    Write-Host "[OK] Logged in as: $whoami" -ForegroundColor Green
} catch {
    Write-Host "[INFO] Not logged in. Running fly auth login..." -ForegroundColor Yellow
    fly auth login
}

Write-Host ""
Write-Host "Setting secrets for app: $APP_NAME" -ForegroundColor Cyan
Write-Host "----------------------------------------"

# ===== REQUIRED SECRETS =====
# Replace <YOUR_*> placeholders with values from your .env file

# Telegram Bot
Write-Host "Setting TELEGRAM_BOT_TOKEN..." -ForegroundColor Yellow
fly secrets set TELEGRAM_BOT_TOKEN="<YOUR_TELEGRAM_BOT_TOKEN>" -a $APP_NAME

Write-Host "Setting TELEGRAM_ADMIN_CHAT_ID..." -ForegroundColor Yellow
fly secrets set TELEGRAM_ADMIN_CHAT_ID="<YOUR_ADMIN_CHAT_ID>" -a $APP_NAME

# Primary Database (Neon)
Write-Host "Setting DATABASE_URL..." -ForegroundColor Yellow
fly secrets set DATABASE_URL="<YOUR_NEON_DATABASE_URL>" -a $APP_NAME

# Atlas CMMS Database
Write-Host "Setting ATLAS_DATABASE_URL..." -ForegroundColor Yellow
fly secrets set ATLAS_DATABASE_URL="<YOUR_ATLAS_DATABASE_URL>" -a $APP_NAME

# LLM APIs (Photo Pipeline)
Write-Host "Setting GROQ_API_KEY..." -ForegroundColor Yellow
fly secrets set GROQ_API_KEY="<YOUR_GROQ_API_KEY>" -a $APP_NAME

Write-Host "Setting DEEPSEEK_API_KEY..." -ForegroundColor Yellow
fly secrets set DEEPSEEK_API_KEY="<YOUR_DEEPSEEK_API_KEY>" -a $APP_NAME

Write-Host "Setting ANTHROPIC_API_KEY..." -ForegroundColor Yellow
fly secrets set ANTHROPIC_API_KEY="<YOUR_ANTHROPIC_API_KEY>" -a $APP_NAME

Write-Host "Setting GOOGLE_API_KEY..." -ForegroundColor Yellow
fly secrets set GOOGLE_API_KEY="<YOUR_GOOGLE_API_KEY>" -a $APP_NAME

Write-Host "Setting OPENAI_API_KEY..." -ForegroundColor Yellow
fly secrets set OPENAI_API_KEY="<YOUR_OPENAI_API_KEY>" -a $APP_NAME

# n8n Webhooks
Write-Host "Setting N8N_WEBHOOK_BASE_URL..." -ForegroundColor Yellow
fly secrets set N8N_WEBHOOK_BASE_URL="<YOUR_N8N_WEBHOOK_BASE_URL>" -a $APP_NAME

# Langfuse Observability (optional)
Write-Host "Setting LANGFUSE_PUBLIC_KEY..." -ForegroundColor Yellow
fly secrets set LANGFUSE_PUBLIC_KEY="<YOUR_LANGFUSE_PUBLIC_KEY>" -a $APP_NAME

Write-Host "Setting LANGFUSE_SECRET_KEY..." -ForegroundColor Yellow
fly secrets set LANGFUSE_SECRET_KEY="<YOUR_LANGFUSE_SECRET_KEY>" -a $APP_NAME

Write-Host "Setting LANGFUSE_BASE_URL..." -ForegroundColor Yellow
fly secrets set LANGFUSE_BASE_URL="https://us.cloud.langfuse.com" -a $APP_NAME

Write-Host ""
Write-Host "----------------------------------------"
Write-Host "[OK] All secrets set!" -ForegroundColor Green
Write-Host ""

# Verify secrets
Write-Host "Verifying secrets..." -ForegroundColor Cyan
fly secrets list -a $APP_NAME

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Deploying application..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Deploy
fly deploy -a $APP_NAME

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Check status:  fly status -a $APP_NAME" -ForegroundColor Yellow
Write-Host "View logs:     fly logs -a $APP_NAME" -ForegroundColor Yellow
Write-Host "Health check:  https://$APP_NAME.fly.dev/health" -ForegroundColor Yellow
Write-Host ""
