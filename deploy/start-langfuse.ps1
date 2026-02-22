# Start Langfuse locally via official Docker Compose (for integration tests / dev).
# Usage: from repo root, run: .\deploy\start-langfuse.ps1
# Then open http://localhost:3000 and create project + API keys; set LANGFUSE_* in .env.

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$LangfuseDir = if ($env:LANGFUSE_DIR) { $env:LANGFUSE_DIR } else { Join-Path $RepoRoot ".langfuse" }

if (-not (Test-Path $LangfuseDir)) {
    Write-Host "Cloning Langfuse into $LangfuseDir ..."
    git clone --depth 1 https://github.com/langfuse/langfuse.git $LangfuseDir
}

Push-Location $LangfuseDir
try {
    Write-Host "Starting Langfuse (docker compose up -d) ..."
    docker compose up -d
    Write-Host "Wait 2-3 minutes for langfuse-web to be Ready. Then open http://localhost:3000"
    Write-Host "Create a project and add LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY to $RepoRoot\.env"
} finally {
    Pop-Location
}
