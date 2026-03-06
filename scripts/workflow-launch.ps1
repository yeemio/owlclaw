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
        [string]$CommandText,
        [string]$StartupType = "cli"
    )

    if ($DryRun) {
        Write-Output ("launch:{0}:{1}:{2}:{3}" -f $WindowTitle, $Workdir, $StartupType, $CommandText)
        return $null
    }

    $wt = Get-Command "wt.exe" -ErrorAction SilentlyContinue
    if ($null -ne $wt -and $StartupType -eq "direct_cli") {
        return Start-Process -PassThru -FilePath $wt.Source -ArgumentList @(
            "-w",
            "new",
            "--title",
            $WindowTitle,
            "-d",
            $Workdir,
            $CommandText
        )
    }

    $script = @"
Set-Location '$Workdir'
`$Host.UI.RawUI.WindowTitle = '$WindowTitle'
$CommandText
"@
    $encoded = New-EncodedCommand -ScriptText $script

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

function Get-LaunchLogPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [string]$Agent
    )

    $logDir = Join-Path $RepoRoot ".kiro\runtime\launch-logs"
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    return (Join-Path $logDir "$Agent.log")
}

function Wait-WorkflowLaunchHealthy {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [string]$Agent,
        [Parameter(Mandatory = $true)]
        [int]$ProcessId,
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

        $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
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

function Write-LaunchState {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [string]$Agent,
        [Parameter(Mandatory = $true)]
        [string]$Status,
        [int]$ProcessId = 0,
        [string]$Note = "",
        [int]$ExitCode = -2147483648
    )

    $args = @(
        "run",
        "python",
        "scripts/workflow_launch_state.py",
        "--repo-root",
        $RepoRoot,
        "update",
        "--agent",
        $Agent,
        "--status",
        $Status
    )
    if ($ProcessId -gt 0) {
        $args += @("--pid", "$ProcessId")
    }
    if ($Note) {
        $args += @("--note", $Note)
    }
    if ($ExitCode -ne -2147483648) {
        $args += @("--exit-code", "$ExitCode")
    }
    $args += "--json"
    & poetry @args | Out-Null
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
    $maxAttempts = if ($role.startup.max_attempts) { [int]$role.startup.max_attempts } else { 1 }
    $retryDelaySeconds = if ($role.startup.retry_delay_seconds) { [int]$role.startup.retry_delay_seconds } else { 3 }
    $logPath = Get-LaunchLogPath -RepoRoot $mainRepo -Agent ([string]$role.agent)
    $command = $startupCommand

    if ($startupType -eq "audit_agent") {
        $summary = [string]$role.startup.audit_summary
        $interval = [int]$role.startup.heartbeat_interval_seconds
        $command = @"
`$null = Start-Job -ScriptBlock { param(`$repo) Set-Location `$repo; poetry run python scripts/workflow_audit_heartbeat.py --agent $($role.agent) --status idle --summary `"$summary`" --interval $interval } -ArgumentList '$($role.repo_path)'
poetry run python scripts/workflow_audit_state.py update --agent $($role.agent) --status idle --summary `"$summary`" | Out-Null
`$workflowLaunchAttempts = $maxAttempts
`$workflowRetryDelaySeconds = $retryDelaySeconds
1..`$workflowLaunchAttempts | ForEach-Object {
    `$workflowAttempt = `$_
    poetry run python scripts/workflow_launch_state.py --repo-root '$mainRepo' update --agent $($role.agent) --status starting --pid `$PID --note `"attempt `$workflowAttempt/$maxAttempts`" --json | Out-Null
    Add-Content -Path '$logPath' -Value ("[{0}] attempt {1}/{2} starting" -f [DateTime]::UtcNow.ToString("o"), `$workflowAttempt, $maxAttempts)
    `$workflowLaunchMarker = Start-Job -ScriptBlock {
        param(`$repoRoot, `$agent, `$delaySeconds, `$pidValue, `$attempt)
        Start-Sleep -Seconds `$delaySeconds
        Set-Location `$repoRoot
        poetry run python scripts/workflow_launch_state.py --repo-root `$repoRoot update --agent `$agent --status running --pid `$pidValue --note `"startup grace passed on attempt `$attempt`" --json | Out-Null
    } -ArgumentList '$mainRepo', '$($role.agent)', $StartupGraceSeconds, `$PID, `$workflowAttempt
    `$workflowStartTime = Get-Date
    try {
        Invoke-Expression $startupCommand
    }
    finally {
        if (`$workflowLaunchMarker) {
            Stop-Job -Job `$workflowLaunchMarker -ErrorAction SilentlyContinue | Out-Null
            Remove-Job -Job `$workflowLaunchMarker -Force -ErrorAction SilentlyContinue | Out-Null
        }
    }
    `$workflowExitCode = `$LASTEXITCODE
    `$workflowRuntimeSeconds = ((Get-Date) - `$workflowStartTime).TotalSeconds
    Add-Content -Path '$logPath' -Value ("[{0}] attempt {1}/{2} exited code={3} runtime_seconds={4}" -f [DateTime]::UtcNow.ToString("o"), `$workflowAttempt, $maxAttempts, `$workflowExitCode, [Math]::Round(`$workflowRuntimeSeconds, 2))
    if (`$workflowRuntimeSeconds -ge $StartupGraceSeconds) {
        poetry run python scripts/workflow_launch_state.py --repo-root '$mainRepo' update --agent $($role.agent) --status exited --pid `$PID --exit-code `$workflowExitCode --note `"cli exited after running`" --json | Out-Null
        return
    }
    if (`$workflowAttempt -lt `$workflowLaunchAttempts) {
        poetry run python scripts/workflow_launch_state.py --repo-root '$mainRepo' update --agent $($role.agent) --status starting --pid `$PID --exit-code `$workflowExitCode --note `"retrying after quick exit on attempt `$workflowAttempt`" --json | Out-Null
        Start-Sleep -Seconds `$workflowRetryDelaySeconds
    }
    else {
        poetry run python scripts/workflow_launch_state.py --repo-root '$mainRepo' update --agent $($role.agent) --status exited --pid `$PID --exit-code `$workflowExitCode --note `"cli returned to powershell after retries`" --json | Out-Null
    }
}
"@
    }

    $targets += @{
        Agent = [string]$role.agent
        Title = [string]$role.window_title
        Workdir = [string]$role.repo_path
        Command = $command
        StartupType = $startupType
        MaxAttempts = $maxAttempts
        RetryDelaySeconds = $retryDelaySeconds
    }
}

$windowManifest = @{}
foreach ($target in $targets) {
    $started = $false
    $attempt = 0
    while (-not $started -and $attempt -lt $target.MaxAttempts) {
        $attempt += 1
        if (-not $DryRun) {
            Write-LaunchState -RepoRoot $mainRepo -Agent $target.Agent -Status "starting" -Note ("attempt {0}/{1}" -f $attempt, $target.MaxAttempts)
            Add-Content -Path (Get-LaunchLogPath -RepoRoot $mainRepo -Agent $target.Agent) -Value ("[{0}] attempt {1}/{2} launching via {3}" -f [DateTime]::UtcNow.ToString("o"), $attempt, $target.MaxAttempts, $target.StartupType)
        }

        $process = Start-WorkflowWindow -WindowTitle $target.Title -Workdir $target.Workdir -CommandText $target.Command -StartupType $target.StartupType
        if (-not $DryRun -and $null -ne $process) {
            $hwnd = Get-WindowHandleByExactTitle -WindowTitle $target.Title
            $windowManifest[$target.Agent] = @{
                pid = $process.Id
                hwnd = $hwnd
                title = $target.Title
                workdir = $target.Workdir
            }
            Save-WindowManifest -RepoRoot $mainRepo -Windows $windowManifest

            if ($target.StartupType -eq "direct_cli") {
                Start-Sleep -Seconds $StartupGraceSeconds
                $alive = Get-Process -Id $process.Id -ErrorAction SilentlyContinue
                if ($null -ne $alive) {
                    Write-LaunchState -RepoRoot $mainRepo -Agent $target.Agent -Status "running" -ProcessId $process.Id -Note ("startup grace passed on attempt {0}" -f $attempt)
                    $started = $true
                }
                else {
                    Write-LaunchState -RepoRoot $mainRepo -Agent $target.Agent -Status "exited" -ProcessId $process.Id -ExitCode 1 -Note ("direct cli exited before grace on attempt {0}" -f $attempt)
                }
            }
            else {
                $health = Wait-WorkflowLaunchHealthy -RepoRoot $mainRepo -Agent $target.Agent -ProcessId $process.Id -TimeoutSeconds $StartupTimeoutSeconds
                if ($health.ok) {
                    $started = $true
                }
                else {
                    Write-Error ("Launch failed for {0}: {1}" -f $target.Agent, $health.reason)
                }
            }
        }

        if (-not $started -and -not $DryRun) {
            if ($attempt -lt $target.MaxAttempts) {
                Start-Sleep -Seconds $target.RetryDelaySeconds
            }
            elseif (-not $ContinueOnLaunchFailure) {
                Write-Error ("Launch failed for {0}: exhausted retries" -f $target.Agent)
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
