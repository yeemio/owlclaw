# Allow inbound TCP 5432 for PostgreSQL (so Docker containers can connect via host.docker.internal).
# Run as Administrator: Right-click -> Run with PowerShell (Admin), or: Start-Process powershell -Verb RunAs -ArgumentList '-File', 'deploy\windows-firewall-5432.ps1'

$ruleName = "PostgreSQL 5432 (OwlClaw/Hatchet)"
$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Rule '$ruleName' already exists."
    exit 0
}
New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Protocol TCP -LocalPort 5432 -Action Allow
Write-Host "Added firewall rule: $ruleName"
