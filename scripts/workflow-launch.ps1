param(
    [string]$ConfigPath = "D:\AI\owlclaw\.kiro\workflow_terminal_config.json",
    [int]$LaunchSpacingMilliseconds = 1200,
    [int]$ControllerDelaySeconds = 6,
    [int]$ControlInterval = 20,
    [int]$LayoutDelaySeconds = 8,
    [int]$StartupGraceSeconds = 8,
    [int]$StartupTimeoutSeconds = 30,
    [switch]$ContinueOnLaunchFailure,
    [switch]$SkipController,
    [switch]$DryRun,
    [switch]$SkipLayout
)

Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class WorkflowWindowLayout
{
    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
}
"@

function Get-WindowManifestPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    return (Join-Path $RepoRoot ".kiro\runtime\terminal-windows.json")
}

function Save-WindowManifest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [hashtable]$Windows
    )

    $runtimeDir = Join-Path $RepoRoot ".kiro\runtime"
    if (-not (Test-Path $runtimeDir)) {
        New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
    }

    $payload = @{
        generated_at = (Get-Date).ToUniversalTime().ToString("o")
        windows = $Windows
    }

    $manifestPath = Get-WindowManifestPath -RepoRoot $RepoRoot
    $payload | ConvertTo-Json -Depth 6 | Set-Content -Path $manifestPath -Encoding UTF8
}

function Get-WindowHandleByExactTitle {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WindowTitle,
        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $process = Get-Process | Where-Object { $_.MainWindowTitle -eq $WindowTitle } | Select-Object -First 1
        if ($null -ne $process -and $process.MainWindowHandle -ne 0) {
            return [Int64]$process.MainWindowHandle
        }
        Start-Sleep -Milliseconds 400
    }

    return [Int64]0
}

function New-EncodedCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptText
    )

    return [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($ScriptText))
}

function Start-WorkflowWindow {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WindowTitle,
        [Parameter(Mandatory = $true)]
        [string]$Workdir,
        [Parameter(Mandatory = $true)]
        [string]$CommandText
    )

    $script = @"
Set-Location '$Workdir'
`$Host.UI.RawUI.WindowTitle = '$WindowTitle'
$CommandText
"@

    if ($DryRun) {
        Write-Output ("launch:{0}:{1}:{2}" -f $WindowTitle, $Workdir, $CommandText)
        return $null
    }

    $encoded = New-EncodedCommand -ScriptText $script
    $wt = Get-Command "wt.exe" -ErrorAction SilentlyContinue
    if ($null -ne $wt) {
        return Start-Process -PassThru -FilePath $wt.Source -ArgumentList @(
            "-w",
            "new",
            "--title",
            $WindowTitle,
            "powershell.exe",
            "-NoExit",
            "-EncodedCommand",
            $encoded
        )
    }

    return Start-Process -PassThru -FilePath "powershell.exe" -ArgumentList @("-NoExit", "-EncodedCommand", $encoded)
}

function Get-LaunchStatePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [string]$Agent
    )

    return (Join-Path $RepoRoot ".kiro\runtime\launch-state\$Agent.json")
}

function Wait-WorkflowLaunchHealthy {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [string]$Agent,
        [Parameter(Mandatory = $true)]
        [int]$Pid,
        [int]$TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $statePath = Get-LaunchStatePath -RepoRoot $RepoRoot -Agent $Agent

    while ((Get-Date) -lt $deadline) {
        if (Test-Path $statePath) {
            $state = Get-Content $statePath -Raw | ConvertFrom-Json
            if ($state.status -eq "running") {
                return @{
                    ok = $true
                    reason = "running"
                    state = $state
                }
            }
            if ($state.status -eq "exited") {
                return @{
                    ok = $false
                    reason = "exited"
                    state = $state
                }
            }
        }

        $process = Get-Process -Id $Pid -ErrorAction SilentlyContinue
        if ($null -eq $process) {
            return @{
                ok = $false
                reason = "window_process_missing"
                state = $null
            }
        }

        Start-Sleep -Milliseconds 500
    }

    return @{
        ok = $false
        reason = "startup_timeout"
        state = $null
    }
}

function Get-WorkflowWindowHandle {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WindowTitle,
        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $process = Get-Process | Where-Object { $_.MainWindowTitle -eq $WindowTitle } | Select-Object -First 1
        if ($null -ne $process) {
            return $process.MainWindowHandle
        }
        Start-Sleep -Milliseconds 400
    }

    return [IntPtr]::Zero
}

function Set-WorkflowGridLayout {
    param(
        [Parameter(Mandatory = $true)]
        [array]$WindowTitles
    )

    Add-Type -AssemblyName System.Windows.Forms
    $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
    $columns = 3
    $rows = 2
    $width = [Math]::Floor($bounds.Width / $columns)
    $height = [Math]::Floor($bounds.Height / $rows)

    for ($index = 0; $index -lt $WindowTitles.Count; $index++) {
        $handle = Get-WorkflowWindowHandle -WindowTitle $WindowTitles[$index]
        if ($handle -eq [IntPtr]::Zero) {
            continue
        }

        $column = $index % $columns
        $row = [Math]::Floor($index / $columns)
        $x = $bounds.Left + ($column * $width)
        $y = $bounds.Top + ($row * $height)
        [WorkflowWindowLayout]::MoveWindow($handle, $x, $y, $width, $height, $true) | Out-Null
    }
}

$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
$mainRole = $config.roles | Where-Object { $_.agent -eq "main" } | Select-Object -First 1
$mainRepo = [string]$mainRole.repo_path

$targets = @()
foreach ($role in $config.roles) {
    $startupType = [string]$role.startup.type
    $startupCommand = [string]$role.startup.command
    $command = @"
poetry run python scripts/workflow_launch_state.py --repo-root '$mainRepo' update --agent $($role.agent) --status starting --json | Out-Null
`$workflowLaunchMarker = Start-Job -ScriptBlock {
    param(`$repoRoot, `$agent, `$delaySeconds, `$pidValue)
    Start-Sleep -Seconds `$delaySeconds
    Set-Location `$repoRoot
    poetry run python scripts/workflow_launch_state.py --repo-root `$repoRoot update --agent `$agent --status running --pid `$pidValue --note `"startup grace passed`" --json | Out-Null
} -ArgumentList '$mainRepo', '$($role.agent)', $StartupGraceSeconds, `$PID
try {
    $startupCommand
}
finally {
    if (`$workflowLaunchMarker) {
        Stop-Job -Job `$workflowLaunchMarker -ErrorAction SilentlyContinue | Out-Null
        Remove-Job -Job `$workflowLaunchMarker -Force -ErrorAction SilentlyContinue | Out-Null
    }
    poetry run python scripts/workflow_launch_state.py --repo-root '$mainRepo' update --agent $($role.agent) --status exited --pid `$PID --exit-code `$LASTEXITCODE --note `"cli returned to powershell`" --json | Out-Null
}
"@

    if ($startupType -eq "audit_agent") {
        $summary = [string]$role.startup.audit_summary
        $interval = [int]$role.startup.heartbeat_interval_seconds
        $command = @"
poetry run python scripts/workflow_launch_state.py --repo-root '$mainRepo' update --agent $($role.agent) --status starting --json | Out-Null
`$workflowLaunchMarker = Start-Job -ScriptBlock {
    param(`$repoRoot, `$agent, `$delaySeconds, `$pidValue)
    Start-Sleep -Seconds `$delaySeconds
    Set-Location `$repoRoot
    poetry run python scripts/workflow_launch_state.py --repo-root `$repoRoot update --agent `$agent --status running --pid `$pidValue --note `"startup grace passed`" --json | Out-Null
} -ArgumentList '$mainRepo', '$($role.agent)', $StartupGraceSeconds, `$PID
try {
    `$null = Start-Job -ScriptBlock { param(`$repo) Set-Location `$repo; poetry run python scripts/workflow_audit_heartbeat.py --agent $($role.agent) --status idle --summary `"$summary`" --interval $interval } -ArgumentList '$($role.repo_path)'
    poetry run python scripts/workflow_audit_state.py update --agent $($role.agent) --status idle --summary `"$summary`" | Out-Null
    $startupCommand
}
finally {
    if (`$workflowLaunchMarker) {
        Stop-Job -Job `$workflowLaunchMarker -ErrorAction SilentlyContinue | Out-Null
        Remove-Job -Job `$workflowLaunchMarker -Force -ErrorAction SilentlyContinue | Out-Null
    }
    poetry run python scripts/workflow_launch_state.py --repo-root '$mainRepo' update --agent $($role.agent) --status exited --pid `$PID --exit-code `$LASTEXITCODE --note `"cli returned to powershell`" --json | Out-Null
}
"@
    }

    $targets += @{
        Agent = [string]$role.agent
        Title = [string]$role.window_title
        Workdir = [string]$role.repo_path
        Command = $command
    }
}

$windowManifest = @{}
foreach ($target in $targets) {
    $process = Start-WorkflowWindow -WindowTitle $target.Title -Workdir $target.Workdir -CommandText $target.Command
    if (-not $DryRun -and $null -ne $process) {
        $hwnd = Get-WindowHandleByExactTitle -WindowTitle $target.Title
        $windowManifest[$target.Agent] = @{
            pid = $process.Id
            hwnd = $hwnd
            title = $target.Title
            workdir = $target.Workdir
        }
        Save-WindowManifest -RepoRoot $mainRepo -Windows $windowManifest
        $health = Wait-WorkflowLaunchHealthy -RepoRoot $mainRepo -Agent $target.Agent -Pid $process.Id -TimeoutSeconds $StartupTimeoutSeconds
        if (-not $health.ok) {
            Write-Error ("Launch failed for {0}: {1}" -f $target.Agent, $health.reason)
            if (-not $ContinueOnLaunchFailure) {
                exit 1
            }
        }
    }
    if (-not $DryRun) {
        Start-Sleep -Milliseconds $LaunchSpacingMilliseconds
    }
}

if (-not $SkipLayout -and -not $DryRun) {
    Start-Sleep -Seconds $LayoutDelaySeconds
    Set-WorkflowGridLayout -WindowTitles ($targets | ForEach-Object { $_.Title })
}

if (-not $SkipController) {
    $controllerCommand = "Start-Sleep -Seconds $ControllerDelaySeconds; pwsh ./scripts/workflow-terminal-control-console.ps1 -Interval $ControlInterval"
    Start-WorkflowWindow -WindowTitle "owlclaw-control" -Workdir $mainRepo -CommandText $controllerCommand
}
