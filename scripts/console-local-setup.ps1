param(
    [switch]$SkipDbInit,
    [int]$Port = 8000
)

# OwlClaw Console local setup
# Example:
#   $env:PG_PASSWORD='your_password'; ./scripts/console-local-setup.ps1
#   ./scripts/console-local-setup.ps1 -SkipDbInit -Port 18000

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not (Get-Command poetry -ErrorAction SilentlyContinue)) {
    Write-Host "Poetry is not installed or not in PATH."
    exit 1
}

if (-not $SkipDbInit) {
    if (-not $env:PG_PASSWORD) {
        Write-Host "Set postgres password first: `$env:PG_PASSWORD = 'your_postgres_password'"
        exit 1
    }

    $adminUrl = "postgresql://postgres:$env:PG_PASSWORD@127.0.0.1:5432/postgres"

    Write-Host "Creating owlclaw database and role..."
    poetry run owlclaw db init --admin-url $adminUrl --skip-hatchet
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "Running migrations..."
    poetry run owlclaw db migrate
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
else {
    Write-Host "Skip DB init/migrate by request."
}

Write-Host "Starting Console on port $Port..."
Write-Host "Tip: for websocket message validation, install websocket extras:"
Write-Host "  poetry run python -m pip install \"uvicorn[standard]\""
poetry run owlclaw start --port $Port
