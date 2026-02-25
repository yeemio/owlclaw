param(
    [switch]$UnitOnly,
    [switch]$KeepUp
)

$ErrorActionPreference = "Stop"

function Stop-TestCompose {
    docker compose -f docker-compose.test.yml down | Out-Null
}

if (-not $KeepUp) {
    Register-EngineEvent PowerShell.Exiting -Action { Stop-TestCompose } | Out-Null
}

docker compose -f docker-compose.test.yml up -d | Out-Null

Write-Host "Waiting for postgres healthcheck..."
$containerId = docker compose -f docker-compose.test.yml ps -q postgres
for ($i = 0; $i -lt 30; $i++) {
    $status = docker inspect --format '{{.State.Health.Status}}' $containerId 2>$null
    if ($status -eq "healthy") {
        break
    }
    Start-Sleep -Seconds 2
}

if ($UnitOnly) {
    poetry run pytest tests/unit/ -q
} else {
    poetry run pytest tests/unit/ tests/integration/ -m "not e2e" -q
}

if (-not $KeepUp) {
    Stop-TestCompose
}
