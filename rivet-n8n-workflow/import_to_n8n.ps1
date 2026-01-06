# RIVET Pro - n8n Workflow Import Script (PowerShell)
# Usage: .\import_to_n8n.ps1 [-N8nUrl "http://localhost:5678"] [-ApiKey "your-key"]

param(
    [string]$N8nUrl = $env:N8N_URL ?? "http://localhost:5678",
    [string]$ApiKey = $env:N8N_API_KEY,
    [string]$WorkflowFile = "rivet_workflow.json"
)

# Colors
function Write-Success { Write-Host "✅ $args" -ForegroundColor Green }
function Write-Error-Custom { Write-Host "❌ $args" -ForegroundColor Red }
function Write-Warning-Custom { Write-Host "⚠️  $args" -ForegroundColor Yellow }
function Write-Info { Write-Host "ℹ️  $args" -ForegroundColor Cyan }

# Banner
Write-Host "========================================" -ForegroundColor Blue
Write-Host "RIVET Pro - n8n Workflow Import" -ForegroundColor Blue
Write-Host "========================================`n" -ForegroundColor Blue

# Check API key
if (-not $ApiKey) {
    Write-Error-Custom "N8N_API_KEY not set"
    Write-Host "`nOptions:"
    Write-Host "  1. Set env var: `$env:N8N_API_KEY='your-key'"
    Write-Host "  2. Pass as parameter: -ApiKey 'your-key'"
    Write-Host "`nTo get your API key:"
    Write-Host "  n8n → Settings → API → Generate API Key"
    exit 1
}

# Check workflow file
if (-not (Test-Path $WorkflowFile)) {
    Write-Error-Custom "Workflow file not found: $WorkflowFile"
    exit 1
}

Write-Success "Found workflow file: $WorkflowFile"
Write-Info "n8n URL: $N8nUrl`n"

# Test connection
Write-Host "Testing n8n connection..."
try {
    $headers = @{
        "X-N8N-API-KEY" = $ApiKey
        "Accept" = "application/json"
    }

    $response = Invoke-WebRequest -Uri "$N8nUrl/api/v1/workflows" -Headers $headers -Method GET -ErrorAction Stop

    if ($response.StatusCode -eq 200) {
        Write-Success "Connected to n8n`n"
    }
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 401) {
        Write-Error-Custom "Authentication failed. Check your API key."
    } else {
        Write-Error-Custom "Connection failed: $($_.Exception.Message)"
        Write-Host "Make sure n8n is running: n8n start"
    }
    exit 1
}

# Import workflow
Write-Host "📤 Importing workflow..."
try {
    $workflowContent = Get-Content $WorkflowFile -Raw

    $headers = @{
        "X-N8N-API-KEY" = $ApiKey
        "Content-Type" = "application/json"
        "Accept" = "application/json"
    }

    $response = Invoke-RestMethod -Uri "$N8nUrl/api/v1/workflows" -Headers $headers -Method POST -Body $workflowContent -ErrorAction Stop

    Write-Host "`n"
    Write-Success "Workflow imported successfully!"
    Write-Info "   ID: $($response.id)"
    Write-Info "   Name: $($response.name)"
    Write-Info "   Nodes: $($response.nodes.Count)"
    Write-Info "   URL: $N8nUrl/workflow/$($response.id)`n"

    Write-Warning-Custom "📋 Next Steps:"
    Write-Host "   1. Open workflow: $N8nUrl/workflow/$($response.id)"
    Write-Host "   2. Configure credentials:"
    Write-Host "      - Telegram Bot (token from .env)"
    Write-Host "      - Tavily API (get from tavily.com)"
    Write-Host "      - Atlas CMMS API (from admin panel)"
    Write-Host "   3. Set variables in n8n UI:"
    Write-Host "      - GOOGLE_API_KEY (from .env)"
    Write-Host "      - ATLAS_CMMS_URL (your CMMS instance)"
    Write-Host "   4. Activate workflow (toggle switch)"
    Write-Host "   5. Test with Telegram bot`n"

    # Open in browser
    $openBrowser = Read-Host "Open workflow in browser? (Y/n)"
    if ($openBrowser -ne 'n' -and $openBrowser -ne 'N') {
        Start-Process "$N8nUrl/workflow/$($response.id)"
    }

} catch {
    Write-Host "`n"
    Write-Error-Custom "Import failed: $($_.Exception.Message)"
    if ($_.ErrorDetails.Message) {
        Write-Host "Response: $($_.ErrorDetails.Message)"
    }
    exit 1
}
