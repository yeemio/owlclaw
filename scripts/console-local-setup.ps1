# OwlClaw Console local setup
# Prereqs: PostgreSQL running; set $env:PG_PASSWORD to your postgres admin password before running.

$adminUrl = "postgresql://postgres:$env:PG_PASSWORD@127.0.0.1:5432/postgres"
if (-not $env:PG_PASSWORD) {
    Write-Host "Set postgres password first: `$env:PG_PASSWORD = 'your_postgres_password'"
    exit 1
}

Set-Location $PSScriptRoot\..

Write-Host "Creating owlclaw database and role..."
poetry run owlclaw db init --admin-url $adminUrl --skip-hatchet

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Running migrations..."
poetry run owlclaw db migrate

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Starting Console..."
poetry run owlclaw start
