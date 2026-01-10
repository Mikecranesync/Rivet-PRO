# ======================================================================
# RIVET MCP Setup for n8n Integration (Dual Method)
# ======================================================================
# This script configures n8n MCP server for Claude Code
# Supports BOTH native n8n MCP and third-party n8n-mcp package
#
# Usage:
#   .\scripts\setup_mcp_dual.ps1
#
# What it does:
#   1. Lets you choose: Native MCP or n8n-mcp package (or both)
#   2. Prompts for n8n cloud URL
#   3. Prompts for appropriate API key(s)
#   4. Detects config directory (Windows/Mac/Linux)
#   5. Backs up existing .mcp.json (if exists)
#   6. Generates MCP config JSON with both servers
#   7. Writes to ~/.config/claude-code/mcp.json
#   8. Displays success message with next steps
# ======================================================================

# Color functions
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
Write-Host "  Dual Method Support                  " -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# ======================================================================
# METHOD SELECTION
# ======================================================================

Write-Info "Choose your MCP integration method:"
Write-Host ""
Write-Host "1. n8n Native MCP (RECOMMENDED)"
Write-Host "   - Uses n8n's built-in MCP server"
Write-Host "   - Direct protocol support"
Write-Host "   - Requires MCP Server token (Settings → API → MCP Server)"
Write-Host "   - Best for: Direct Claude integration"
Write-Host ""
Write-Host "2. n8n-mcp Package"
Write-Host "   - Uses third-party npm package"
Write-Host "   - 13 MCP tools for workflow CRUD"
Write-Host "   - Requires API Key (Settings → API → Generate Key)"
Write-Host "   - Best for: Programmatic workflow management"
Write-Host ""
Write-Host "3. Both (Recommended for full functionality)"
Write-Host "   - Configure both methods"
Write-Host "   - Use native for triggers, package for management"
Write-Host "   - Requires both tokens"
Write-Host ""

$method = Read-Host "Enter choice (1, 2, or 3)"

$useNative = $false
$usePackage = $false

switch ($method) {
    "1" { $useNative = $true }
    "2" { $usePackage = $true }
    "3" {
        $useNative = $true
        $usePackage = $true
    }
    default {
        Write-Error-Custom "Invalid choice. Please run again and choose 1, 2, or 3."
        exit 1
    }
}

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
# INPUT: TOKENS (BASED ON METHOD)
# ======================================================================

$mcpServerToken = ""
$apiKey = ""

# Native MCP Token
if ($useNative) {
    Write-Info "Step 2a: MCP Server Token (for Native MCP)"
    Write-Host ""
    Write-Host "How to get MCP Server Token:"
    Write-Host "  1. Open n8n: $n8nUrl"
    Write-Host "  2. Go to: Settings → API"
    Write-Host "  3. Find section: 'MCP Server'"
    Write-Host "  4. Click: 'Create MCP Server Token'"
    Write-Host "  5. Copy the token (starts with 'eyJ...')"
    Write-Host ""
    Write-Host "NOTE: This is different from the regular API key!"
    Write-Host "      Token audience should be 'mcp-server-api'"
    Write-Host ""

    $mcpTokenSecure = Read-Host "Enter MCP Server Token" -AsSecureString
    $mcpServerToken = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($mcpTokenSecure)
    )

    # Validate token format
    if ([string]::IsNullOrWhiteSpace($mcpServerToken)) {
        Write-Error-Custom "Error: MCP Server Token is required"
        exit 1
    }

    if (-not ($mcpServerToken -match "^eyJ")) {
        Write-Warning-Custom "Warning: Token doesn't look like a JWT (should start with 'eyJ')"
        Write-Host ""
        $continue = Read-Host "Continue anyway? (y/n)"
        if ($continue -ne "y") {
            Write-Host "Setup cancelled"
            exit 1
        }
    }

    Write-Success "[OK] MCP Server Token validated"
    Write-Host ""
}

# n8n-mcp Package API Key
if ($usePackage) {
    $stepNum = if ($useNative) { "2b" } else { "2" }
    Write-Info "Step ${stepNum}: API Key (for n8n-mcp Package)"
    Write-Host ""
    Write-Host "How to get API Key:"
    Write-Host "  1. Open n8n: $n8nUrl"
    Write-Host "  2. Go to: Settings → API"
    Write-Host "  3. Click: 'Generate API Key' (NOT MCP Server Token!)"
    Write-Host "  4. Copy the key (starts with 'eyJ...')"
    Write-Host ""
    Write-Host "NOTE: This is the regular API key"
    Write-Host "      Token audience should be 'public-api'"
    Write-Host ""

    $apiKeySecure = Read-Host "Enter API Key" -AsSecureString
    $apiKey = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($apiKeySecure)
    )

    # Validate API key format
    if ([string]::IsNullOrWhiteSpace($apiKey)) {
        Write-Error-Custom "Error: API Key is required"
        exit 1
    }

    if (-not ($apiKey -match "^eyJ")) {
        Write-Warning-Custom "Warning: API key doesn't look like a JWT (should start with 'eyJ')"
        Write-Host ""
        $continue = Read-Host "Continue anyway? (y/n)"
        if ($continue -ne "y") {
            Write-Host "Setup cancelled"
            exit 1
        }
    }

    Write-Success "[OK] API Key validated"
    Write-Host ""
}

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

# Create config object
$mcpServers = @{}

# Add native MCP server
if ($useNative) {
    $mcpServers["n8n-native"] = @{
        command = "npx"
        args = @(
            "-y",
            "supergateway",
            "--streamableHttp",
            "$n8nUrl/mcp-server/http",
            "--header",
            "authorization:Bearer $mcpServerToken"
        )
    }
    Write-Info "✓ Added n8n-native (built-in MCP server)"
}

# Add n8n-mcp package
if ($usePackage) {
    $mcpServers["n8n-mcp"] = @{
        command = "npx"
        args = @("-y", "n8n-mcp")
        env = @{
            MCP_MODE = "stdio"
            LOG_LEVEL = "error"
            DISABLE_CONSOLE_OUTPUT = "true"
            N8N_API_URL = "$n8nUrl/api/v1"
            N8N_API_KEY = $apiKey
            WEBHOOK_SECURITY_MODE = "moderate"
        }
    }
    Write-Info "✓ Added n8n-mcp (npm package, 13 tools)"
}

$config = @{
    mcpServers = $mcpServers
}

# Convert to JSON with proper formatting
$configJson = $config | ConvertTo-Json -Depth 10

Write-Host ""

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
    if ($usePackage) {
        Write-Host "Testing n8n-mcp package connection..."

        try {
            $headers = @{
                "X-N8N-API-KEY" = $apiKey
                "Accept" = "application/json"
            }

            $response = Invoke-WebRequest -Uri "$n8nUrl/api/v1/workflows" -Headers $headers -Method GET -ErrorAction Stop

            if ($response.StatusCode -eq 200) {
                Write-Success "[OK] n8n-mcp package connection successful!"

                # Try to parse workflow count
                try {
                    $workflows = ($response.Content | ConvertFrom-Json).data
                    Write-Info "Found $($workflows.Count) workflows"
                }
                catch {
                    Write-Info "Connected successfully"
                }
            }
        }
        catch {
            Write-Warning-Custom "Warning: n8n-mcp connection test failed: $_"
        }
    }

    if ($useNative) {
        Write-Host ""
        Write-Info "Native MCP connection will be tested when Claude Code starts"
        Write-Host "(supergateway connects on first use)"
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

Write-Info "Configured MCP Servers:"
if ($useNative) {
    Write-Host "  ✓ n8n-native (built-in MCP server)"
}
if ($usePackage) {
    Write-Host "  ✓ n8n-mcp (npm package, 13 tools)"
}
Write-Host ""

Write-Info "Config saved to:"
Write-Host "  $mcpConfigPath"
Write-Host ""

Write-Info "Next steps:"
Write-Host "  1. Restart Claude Code CLI"
Write-Host "     (Close and reopen your terminal)"
Write-Host ""
Write-Host "  2. Test MCP integration:"
if ($useNative) {
    Write-Host "     Ask Claude: 'Trigger the URL validator workflow'"
}
if ($usePackage) {
    Write-Host "     Ask Claude: 'List my n8n workflows'"
}
Write-Host ""
Write-Host "  3. Deploy test workflows (Agent 1):"
Write-Host "     - RIVET-URL-Validator"
Write-Host "     - RIVET-LLM-Judge"
Write-Host "     - RIVET-Test-Runner"
Write-Host ""
Write-Host "  4. Test Python client:"
Write-Host "     python scripts/test_client.py validate-url 'https://example.com'"
Write-Host ""

# ======================================================================
# USAGE GUIDE
# ======================================================================

Write-Info "When to use each method:"
Write-Host ""
if ($useNative) {
    Write-Host "n8n-native (Native MCP):"
    Write-Host "  - Direct workflow triggers"
    Write-Host "  - Claude asks: 'Run the test workflow'"
    Write-Host "  - More direct, official support"
    Write-Host ""
}
if ($usePackage) {
    Write-Host "n8n-mcp (npm Package):"
    Write-Host "  - Workflow management (CRUD)"
    Write-Host "  - Claude asks: 'List/create/update workflows'"
    Write-Host "  - 13 specialized tools"
    Write-Host ""
}

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
