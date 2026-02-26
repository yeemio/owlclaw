param(
    [switch]$Strict
)

$ErrorActionPreference = "Stop"

$requiredFiles = @(
    "examples/cross_lang/java/pom.xml",
    "examples/cross_lang/java/src/main/java/io/owlclaw/examples/crosslang/Main.java",
    "examples/cross_lang/java/src/main/java/io/owlclaw/examples/crosslang/GatewayClient.java",
    "docs/protocol/JAVA_GOLDEN_PATH.md",
    "scripts/cross_lang/trigger_agent.sh",
    "scripts/cross_lang/query_status.sh",
    "scripts/cross_lang/error_scenario.sh"
)

$missing = @()
foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        $missing += $file
    }
}

if ($missing.Count -gt 0) {
    Write-Host "Missing required files:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    exit 1
}

Write-Host "Cross-language baseline files are present." -ForegroundColor Green

if ($Strict) {
    $pom = Get-Content "examples/cross_lang/java/pom.xml" -Raw
    if ($pom -notmatch "maven.compiler.source>17<") {
        Write-Host "Strict check failed: Java source level is not 17." -ForegroundColor Red
        exit 1
    }
    Write-Host "Strict check passed." -ForegroundColor Green
}
