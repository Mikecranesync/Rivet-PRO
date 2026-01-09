# =============================================================================
# RIVET Pro ABB Pipeline Test (PowerShell)
# =============================================================================
# Tests the full pipeline with the ABB ACS580 equipment that started it all.
#
# Usage: .\scripts\test_abb_pipeline.ps1 [-N8nUrl "https://your-instance.app.n8n.cloud"]
# =============================================================================

param(
    [string]$N8nUrl = $env:N8N_CLOUD_URL
)

Write-Host "🚀 RIVET Pro Pipeline Test" -ForegroundColor Cyan
Write-Host "==========================" -ForegroundColor Cyan
Write-Host ""

# Check if URL is configured
if (-not $N8nUrl -or $N8nUrl -like "*your-instance*") {
    Write-Host "ERROR: n8n Cloud URL not configured" -ForegroundColor Red
    Write-Host ""
    Write-Host "Set your n8n Cloud URL:"
    Write-Host '  $env:N8N_CLOUD_URL = "https://your-instance.app.n8n.cloud"'
    Write-Host "  .\scripts\test_abb_pipeline.ps1"
    Write-Host ""
    Write-Host "Or pass it directly:"
    Write-Host '  .\scripts\test_abb_pipeline.ps1 -N8nUrl "https://your-instance.app.n8n.cloud"'
    exit 1
}

$ManualHunterWebhook = "$N8nUrl/webhook/rivet-manual-hunter"

Write-Host "📋 Test Case: ABB ACS580-01-12A5-4" -ForegroundColor Yellow
Write-Host "   This is the equipment that started RIVET Pro"
Write-Host ""
Write-Host "🔗 Target: $N8nUrl"
Write-Host ""

# Test data - the original ABB equipment
$TestData = @{
    manufacturer = "ABB"
    model_number = "ACS580-01-12A5-4"
    product_family = "ACS580"
    chat_id = 123456789
    source = "automated_test"
} | ConvertTo-Json

# =============================================================================
# Test 1: Manual Hunter Direct
# =============================================================================
Write-Host "🔍 Test 1: Manual Hunter Direct Search" -ForegroundColor Cyan
Write-Host "   Endpoint: $ManualHunterWebhook"

$StartTime = Get-Date

try {
    $Response = Invoke-RestMethod -Uri $ManualHunterWebhook -Method Post -Body $TestData -ContentType "application/json" -ErrorAction Stop
    $EndTime = Get-Date
    $Duration = [math]::Round(($EndTime - $StartTime).TotalMilliseconds)
    
    Write-Host "   ✓ Response received (${Duration}ms)" -ForegroundColor Green
}
catch {
    Write-Host "   ❌ FAILED: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "📊 Results:" -ForegroundColor Yellow

$Found = $Response.found -or $Response.manual_found
$PdfUrl = $Response.pdf_url -or $Response.manual_url -or "not_found"
$Tier = $Response.search_tier -or "unknown"
$Confidence = $Response.confidence_score -or 0

Write-Host "   Manual Found:  $Found"
Write-Host "   Search Tier:   $Tier"
Write-Host "   Confidence:    $Confidence%"
Write-Host "   Response Time: ${Duration}ms"
Write-Host "   PDF URL:       $PdfUrl"
Write-Host ""

# =============================================================================
# Validation
# =============================================================================
Write-Host "✅ Validation:" -ForegroundColor Cyan

$Passed = $true

if ($Found) {
    Write-Host "   ✓ Manual found" -ForegroundColor Green
} else {
    Write-Host "   ✗ Manual NOT found" -ForegroundColor Red
    $Passed = $false
}

if ($Tier -in @(1, 2, "1", "2")) {
    Write-Host "   ✓ Search tier acceptable ($Tier)" -ForegroundColor Green
} else {
    Write-Host "   ⚠ Search tier higher than expected ($Tier)" -ForegroundColor Yellow
}

if ($Duration -lt 15000) {
    Write-Host "   ✓ Response time acceptable (${Duration}ms < 15000ms)" -ForegroundColor Green
} else {
    Write-Host "   ⚠ Response time slow (${Duration}ms)" -ForegroundColor Yellow
}

if ($PdfUrl -match "abb|ABB|ACS580") {
    Write-Host "   ✓ PDF URL looks correct" -ForegroundColor Green
} else {
    Write-Host "   ⚠ PDF URL may not be ABB-specific" -ForegroundColor Yellow
}

Write-Host ""

# =============================================================================
# Final Result
# =============================================================================
if ($Passed) {
    Write-Host "═══════════════════════════════════════" -ForegroundColor Green
    Write-Host "   ✅ ABB PIPELINE TEST PASSED" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════" -ForegroundColor Green
    exit 0
} else {
    Write-Host "═══════════════════════════════════════" -ForegroundColor Red
    Write-Host "   ❌ ABB PIPELINE TEST FAILED" -ForegroundColor Red
    Write-Host "═══════════════════════════════════════" -ForegroundColor Red
    Write-Host ""
    Write-Host "Full response:"
    $Response | ConvertTo-Json -Depth 10
    exit 1
}
