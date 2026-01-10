# ======================================================================
# RIVET MCP Setup for n8n Integration
# ======================================================================
# This script configures the n8n-mcp server for Claude Code
# Prompts for n8n URL and API key, generates MCP config
#
# Usage:
#   .\scripts\setup_mcp.ps1
#
# What it does:
#   1. Prompts for n8n cloud URL
#   2. Prompts for n8n API key
#   3. Detects config directory (Windows/Mac/Linux)
#   4. Backs up existing .mcp.json (if exists)
#   5. Generates MCP config JSON
#   6. Writes to ~/.config/claude-code/mcp.json
#   7. Displays success message with next steps
# ======================================================================

# Color functions (matches import_to_n8n.ps1 pattern)
function Write-Success {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Green
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Red
}

function Write-Warning-Custom {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Cyan
}

# ======================================================================
# BANNER
# ======================================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Blue
Write-Host "  RIVET MCP Setup - n8n Integration   " -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# ======================================================================
# INPUT: N8N URL
# ======================================================================

Write-Info "Step 1: n8n Instance URL"
Write-Host ""
Write-Host "Examples:"
Write-Host "  - https://mikecranesync.app.n8n.cloud"
Write-Host "  - https://your-instance.app.n8n.cloud"
Write-Host "  - http://localhost:5678 (local)"
Write-Host ""

$n8nUrl = Read-Host "Enter n8n URL"

# Validate URL format
if ([string]::IsNullOrWhiteSpace($n8nUrl)) {
    Write-Error-Custom "Error: n8n URL is required"
    exit 1
}

if (-not ($n8nUrl -match "^https?://")) {
    Write-Error-Custom "Error: URL must start with http:// or https://"
    Write-Host ""
    Write-Host "Example: https://mikecranesync.app.n8n.cloud"
    exit 1
}

# Remove trailing slash
$n8nUrl = $n8nUrl.TrimEnd('/')

Write-Success "[OK] n8n URL: $n8nUrl"
Write-Host ""

# ======================================================================
# INPUT: API KEY
# ======================================================================

Write-Info "Step 2: n8n API Key"
Write-Host ""
Write-Host "How to get your API key:"
Write-Host "  1. Open n8n: $n8nUrl"
Write-Host "  2. Go to: Settings → API"
Write-Host "  3. Click: Generate API Key"
Write-Host "  4. Copy the key (starts with 'eyJ...')"
Write-Host ""

$apiKey = Read-Host "Enter n8n API Key" -AsSecureString
$apiKeyPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($apiKey)
)

# Validate API key format (JWT should start with 'eyJ')
if ([string]::IsNullOrWhiteSpace($apiKeyPlain)) {
    Write-Error-Custom "Error: API key is required"
    exit 1
}

if (-not ($apiKeyPlain -match "^eyJ")) {
    Write-Warning-Custom "Warning: API key doesn't look like a JWT token (should start with 'eyJ')"
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        Write-Host "Setup cancelled"
        exit 1
    }
}

Write-Success "[OK] API key validated"
Write-Host ""

# ======================================================================
# DETECT CONFIG DIRECTORY
# ======================================================================

Write-Info "Step 3: Detecting config directory..."
Write-Host ""

# Detect OS and config directory
if ($IsWindows -or $env:OS -match "Windows") {
    $configDir = Join-Path $env:USERPROFILE ".config\claude-code"
}
elseif ($IsMacOS -or $env:HOME) {
    $configDir = Join-Path $env:HOME ".config/claude-code"
}
elseif ($IsLinux) {
    $configDir = Join-Path $env:HOME ".config/claude-code"
}
else {
    # Fallback
    $configDir = Join-Path $env:USERPROFILE ".config\claude-code"
}

Write-Info "Config directory: $configDir"

# Create directory if not exists
if (-not (Test-Path $configDir)) {
    Write-Info "Creating config directory..."
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
    Write-Success "[OK] Config directory created"
}
else {
    Write-Success "[OK] Config directory exists"
}

Write-Host ""

# ======================================================================
# BACKUP EXISTING CONFIG
# ======================================================================

$mcpConfigPath = Join-Path $configDir "mcp.json"

if (Test-Path $mcpConfigPath) {
    Write-Warning-Custom "Existing .mcp.json found - creating backup..."

    # Create backup with timestamp
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupPath = Join-Path $configDir "mcp.json.backup.$timestamp"

    Copy-Item -Path $mcpConfigPath -Destination $backupPath
    Write-Success "[OK] Backup saved: $backupPath"
    Write-Host ""
}

# ======================================================================
# GENERATE MCP CONFIG
# ======================================================================

Write-Info "Step 4: Generating MCP config..."
Write-Host ""

# Create config object (matches .mcp.json template)
$config = @{
    mcpServers = @{
        "n8n-mcp" = @{
            command = "npx"
            args = @("-y", "n8n-mcp")
            env = @{
                MCP_MODE = "stdio"
                LOG_LEVEL = "error"
                DISABLE_CONSOLE_OUTPUT = "true"
                N8N_API_URL = "$n8nUrl/api/v1"
                N8N_API_KEY = $apiKeyPlain
                WEBHOOK_SECURITY_MODE = "moderate"
            }
        }
    }
}

# Convert to JSON with proper formatting
$configJson = $config | ConvertTo-Json -Depth 10

# ======================================================================
# WRITE CONFIG FILE
# ======================================================================

try {
    $configJson | Set-Content -Path $mcpConfigPath -Encoding UTF8
    Write-Success "[OK] MCP config written to: $mcpConfigPath"
    Write-Host ""
}
catch {
    Write-Error-Custom "Error writing config file: $_"
    exit 1
}

# ======================================================================
# VALIDATE JSON
# ======================================================================

Write-Info "Step 5: Validating JSON..."
Write-Host ""

try {
    $testConfig = Get-Content -Path $mcpConfigPath -Raw | ConvertFrom-Json
    Write-Success "[OK] JSON is valid"
    Write-Host ""
}
catch {
    Write-Error-Custom "Error: Generated JSON is invalid: $_"
    exit 1
}

# ======================================================================
# CONNECTION TEST (OPTIONAL)
# ======================================================================

Write-Info "Step 6: Testing connection (optional)..."
Write-Host ""

$testConnection = Read-Host "Test connection to n8n? (y/n)"

if ($testConnection -eq "y") {
    Write-Host "Testing connection to $n8nUrl/api/v1/workflows..."

    try {
        $headers = @{
            "X-N8N-API-KEY" = $apiKeyPlain
            "Accept" = "application/json"
        }

        $response = Invoke-WebRequest -Uri "$n8nUrl/api/v1/workflows" -Headers $headers -Method GET -ErrorAction Stop

        if ($response.StatusCode -eq 200) {
            Write-Success "[OK] Connection successful!"

            # Try to parse workflow count
            try {
                $workflows = ($response.Content | ConvertFrom-Json).data
                Write-Info "Found $($workflows.Count) workflows in n8n"
            }
            catch {
                Write-Info "Connected successfully"
            }
        }
        else {
            Write-Warning-Custom "Warning: Unexpected status code: $($response.StatusCode)"
        }
    }
    catch {
        Write-Warning-Custom "Warning: Connection test failed: $_"
        Write-Host ""
        Write-Host "This might be normal if:"
        Write-Host "  - n8n instance is not running"
        Write-Host "  - API key is not activated yet"
        Write-Host "  - Firewall blocking connection"
        Write-Host ""
        Write-Host "MCP config was still saved successfully"
    }

    Write-Host ""
}

# ======================================================================
# SUCCESS MESSAGE
# ======================================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Success "MCP Setup Complete!"
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Info "Config saved to:"
Write-Host "  $mcpConfigPath"
Write-Host ""

Write-Info "Next steps:"
Write-Host "  1. Restart Claude Code CLI"
Write-Host "     (Close and reopen your terminal)"
Write-Host ""
Write-Host "  2. Test MCP integration:"
Write-Host "     Ask Claude: 'List my n8n workflows'"
Write-Host ""
Write-Host "  3. Deploy test workflows (Agent 1):"
Write-Host "     - RIVET-URL-Validator"
Write-Host "     - RIVET-LLM-Judge"
Write-Host "     - RIVET-Test-Runner"
Write-Host ""
Write-Host "  4. Test Python client:"
Write-Host "     python scripts/test_client.py validate-url 'https://example.com'"
Write-Host ""

Write-Success "Setup complete! Happy testing!"
Write-Host ""

# ======================================================================
# OPTIONAL: OPEN N8N
# ======================================================================

$openN8n = Read-Host "Open n8n in browser? (y/n)"

if ($openN8n -eq "y") {
    Start-Process $n8nUrl
}

Write-Host ""
Write-Host "Done!"
