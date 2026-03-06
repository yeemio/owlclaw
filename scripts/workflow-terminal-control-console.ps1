param(
    [int]$Interval = 20,
    [int]$StaleSeconds = 180
)

$repoRoot = (Resolve-Path ".").Path
$controlScript = "scripts/workflow_terminal_control.py"
$focusScript = "scripts/workflow_focus_window.ps1"
$agents = @("main", "review", "codex", "codex-gpt", "audit-a", "audit-b")

function Get-WorkflowWindowPid {
    param(
        [string]$Agent
    )

    $manifestPath = Join-Path $repoRoot ".kiro\runtime\terminal-windows.json"
    if (-not (Test-Path $manifestPath)) {
        return 0
    }

    $manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
    if ($null -eq $manifest.windows) {
        return 0
    }

    $window = $manifest.windows.$Agent
    if ($null -eq $window) {
        return 0
    }

    return [int]$window.pid
}

function Get-WorkflowWindowHandle {
    param(
        [string]$Agent
    )

    $manifestPath = Join-Path $repoRoot ".kiro\runtime\terminal-windows.json"
    if (-not (Test-Path $manifestPath)) {
        return 0
    }

    $manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
    if ($null -eq $manifest.windows) {
        return 0
    }

    $window = $manifest.windows.$Agent
    if ($null -eq $window) {
        return 0
    }

    return [UInt64]$window.hwnd
}

function Show-Help {
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  help               Show this help"
    Write-Host "  pause              Pause automatic delivery"
    Write-Host "  resume             Resume automatic delivery"
    Write-Host "  status             Show pause status"
    Write-Host "  send <agent>       Send one immediate instruction"
    Write-Host "  takeover <agent>   Focus target window for manual takeover"
    Write-Host "  quit               Stop controller"
    Write-Host ""
    Write-Host ("Agents: {0}" -f ($agents -join ", "))
    Write-Host ""
}

function Invoke-Control {
    param(
        [string[]]$Arguments
    )

    & poetry run python $controlScript @Arguments
}

function Set-Paused {
    param(
        [bool]$Paused
    )

    $python = @"
from pathlib import Path
import sys
sys.path.insert(0, str(Path(r'$repoRoot') / 'scripts'))
import workflow_terminal_control
workflow_terminal_control.set_paused(Path(r'$repoRoot'), $($Paused.ToString().ToLower()))
"@
    $python | poetry run python -
}

Show-Help
Write-Host ("Controller loop running every {0}s (stale threshold {1}s). Type a command and press Enter." -f $Interval, $StaleSeconds)

while ($true) {
    Invoke-Control @("--once", "--stale-seconds", "$StaleSeconds", "--json")

    $deadline = (Get-Date).AddSeconds($Interval)
    while ((Get-Date) -lt $deadline) {
        if ([Console]::KeyAvailable) {
            $commandLine = Read-Host "workflow-control"
            if ([string]::IsNullOrWhiteSpace($commandLine)) {
                continue
            }

            $parts = $commandLine.Trim().Split(" ", 2, [System.StringSplitOptions]::RemoveEmptyEntries)
            $command = $parts[0].ToLowerInvariant()
            $target = if ($parts.Length -gt 1) { $parts[1].Trim() } else { "" }

            switch ($command) {
                "help" {
                    Show-Help
                }
                "pause" {
                    Set-Paused -Paused $true
                    Write-Host "paused"
                }
                "resume" {
                    Set-Paused -Paused $false
                    Write-Host "resumed"
                }
                "status" {
                    Invoke-Control @("--once", "--stale-seconds", "$StaleSeconds", "--json")
                }
                "send" {
                    if ($agents -notcontains $target) {
                        Write-Host "unknown agent"
                    }
                    else {
                        Invoke-Control @("--agent", $target, "--once", "--force", "--json")
                    }
                }
                "takeover" {
                    if ($agents -notcontains $target) {
                        Write-Host "unknown agent"
                    }
                    else {
                        $windowTitle = "owlclaw-$target"
                        $handle = Get-WorkflowWindowHandle -Agent $target
                        $pid = Get-WorkflowWindowPid -Agent $target
                        if ($handle -gt 0) {
                            pwsh -NoProfile -File $focusScript -WindowHandle $handle -ProcessId $pid -WindowTitle $windowTitle
                        }
                        elseif ($pid -gt 0) {
                            pwsh -NoProfile -File $focusScript -ProcessId $pid -WindowTitle $windowTitle
                        }
                        else {
                            pwsh -NoProfile -File $focusScript -WindowTitle $windowTitle
                        }
                    }
                }
                "quit" {
                    return
                }
                default {
                    Write-Host "unknown command"
                }
            }
        }

        Start-Sleep -Milliseconds 250
    }
}
