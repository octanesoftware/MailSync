# Manual Mail Sync Trigger Script (PowerShell)
# Usage: .\mailsync.ps1 -SyncName "MyMailSync"
# Example: .\mailsync.ps1 -SyncName "MyMailSync"

param(
    [Parameter(Mandatory=$true)]
    [string]$SyncName,

    [string]$ApiUrl = $env:MAILSYNC_API_URL,
    [string]$ApiKey = $env:MAILSYNC_API_KEY
)

# Default values if not set in environment
if (-not $ApiUrl) {
    $ApiUrl = "http://localhost:5000"
}

if (-not $ApiKey) {
    $ApiKey = "change-me-please"
}

Write-Host "Triggering mail sync: $SyncName" -ForegroundColor Cyan
Write-Host "API URL: $ApiUrl" -ForegroundColor Gray
Write-Host ""

# Prepare request
$headers = @{
    "Content-Type" = "application/json"
    "X-API-Key" = $ApiKey
}

$body = @{
    syncName = $SyncName
} | ConvertTo-Json

# Make API request
try {
    $response = Invoke-RestMethod -Uri "$ApiUrl/sync" -Method Post -Headers $headers -Body $body -ErrorAction Stop

    Write-Host "✓ Sync triggered successfully!" -ForegroundColor Green
    Write-Host ""
    $response | ConvertTo-Json -Depth 10 | Write-Host
    exit 0
}
catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    $errorBody = $_.ErrorDetails.Message

    Write-Host "✗ Sync failed (HTTP $statusCode)" -ForegroundColor Red
    Write-Host ""

    if ($errorBody) {
        try {
            $errorBody | ConvertFrom-Json | ConvertTo-Json -Depth 10 | Write-Host
        }
        catch {
            Write-Host $errorBody
        }
    }
    else {
        Write-Host $_.Exception.Message -ForegroundColor Red
    }

    exit 1
}
