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
    [switch]$UseTerminalController,
    [switch]$UseSupervisorController,
    [switch]$DryRun,
    [switch]$SkipLayout
)

Add-Type @"
using System;
using System.Collections.Generic;
using System.Text;
using System.Runtime.InteropServices;

public static class WorkflowWindowLayout
{
    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool SetWindowPos(
        IntPtr hWnd,
        IntPtr hWndInsertAfter,
        int X,
        int Y,
        int cx,
        int cy,
        uint uFlags);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    public static List<WorkflowWindowInfo> EnumerateWindows()
    {
        var windows = new List<WorkflowWindowInfo>();
        EnumWindows(delegate (IntPtr hWnd, IntPtr lParam)
        {
            if (!IsWindowVisible(hWnd))
            {
                return true;
            }

            var titleBuilder = new StringBuilder(512);
            GetWindowText(hWnd, titleBuilder, titleBuilder.Capacity);
            var title = titleBuilder.ToString() ?? string.Empty;

            uint processId;
            GetWindowThreadProcessId(hWnd, out processId);
            windows.Add(new WorkflowWindowInfo
            {
                Handle = hWnd,
                Title = title,
                ProcessId = processId,
            });
            return true;
        }, IntPtr.Zero);

        return windows;
    }
}

public class WorkflowWindowInfo
{
    public IntPtr Handle { get; set; }
    public string Title { get; set; }
    public uint ProcessId { get; set; }
}
"@

$SWP_NOSIZE = 0x0001
$SWP_NOZORDER = 0x0004
$SWP_NOACTIVATE = 0x0010

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
        $window = [WorkflowWindowLayout]::EnumerateWindows() | Where-Object { $_.Title -eq $WindowTitle } | Select-Object -First 1
        if ($null -ne $window -and $window.Handle -ne [IntPtr]::Zero) {
            return [Int64]$window.Handle
        }
        Start-Sleep -Milliseconds 400
    }

    return [Int64]0
}

function Get-WindowInfoByExactTitle {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WindowTitle,
        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $window = [WorkflowWindowLayout]::EnumerateWindows() | Where-Object { $_.Title -eq $WindowTitle } | Select-Object -First 1
        if ($null -ne $window -and $window.Handle -ne [IntPtr]::Zero) {
            return $window
        }
        Start-Sleep -Milliseconds 400
    }

    return $null
}

function Get-WindowInfoByTitleCandidates {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$WindowTitles,
        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $windows = [WorkflowWindowLayout]::EnumerateWindows()
        foreach ($windowTitle in $WindowTitles) {
            $window = $windows | Where-Object { $_.Title -eq $windowTitle } | Select-Object -First 1
            if ($null -ne $window -and $window.Handle -ne [IntPtr]::Zero) {
                return $window
            }
        }
        foreach ($windowTitle in $WindowTitles) {
            if ([string]::IsNullOrWhiteSpace($windowTitle)) {
                continue
            }
            $window = $windows | Where-Object { $_.Title -like ("*" + $windowTitle + "*") } | Select-Object -First 1
            if ($null -ne $window -and $window.Handle -ne [IntPtr]::Zero) {
                return $window
            }
        }
        Start-Sleep -Milliseconds 400
    }

    return $null
}

function Get-WindowInfoByProcessId {
    param(
        [Parameter(Mandatory = $true)]
        [int]$ProcessId,
        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $windows = [WorkflowWindowLayout]::EnumerateWindows()
        $window = $windows | Where-Object { [int]$_.ProcessId -eq $ProcessId } | Select-Object -First 1
        if ($null -ne $window -and $window.Handle -ne [IntPtr]::Zero) {
            return $window
        }
        Start-Sleep -Milliseconds 400
    }

    return $null
}

function Stop-WorkflowWindowsByExactTitle {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WindowTitle
    )

    $windows = [WorkflowWindowLayout]::EnumerateWindows() | Where-Object { $_.Title -eq $WindowTitle }
    $processIds = @($windows | ForEach-Object { [int]$_.ProcessId } | Sort-Object -Unique)
    foreach ($processId in $processIds) {
        if ($processId -le 0 -or $processId -eq $PID) {
            continue
        }
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
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

    $script = @"
Set-Location '$Workdir'
`$Host.UI.RawUI.WindowTitle = '$WindowTitle'
$CommandText
"@
    $encoded = New-EncodedCommand -ScriptText $script

    return Start-Process -PassThru -WindowStyle Normal -FilePath "powershell.exe" -WorkingDirectory $Workdir -ArgumentList @("-NoExit", "-EncodedCommand", $encoded)
}

function New-DirectCliLaunchCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [string]$Agent,
        [Parameter(Mandatory = $true)]
        [string]$StartupCommand,
        [Parameter(Mandatory = $true)]
        [string]$LogPath,
        [Parameter(Mandatory = $true)]
        [int]$StartupGraceSeconds,
        [Parameter(Mandatory = $true)]
        [int]$MaxAttempts,
        [Parameter(Mandatory = $true)]
        [int]$RetryDelaySeconds
    )

    return @"
`$workflowLaunchAttempts = $MaxAttempts
`$workflowRetryDelaySeconds = $RetryDelaySeconds
1..`$workflowLaunchAttempts | ForEach-Object {
    `$workflowAttempt = `$_
    poetry run python scripts/workflow_launch_state.py --repo-root '$RepoRoot' update --agent $Agent --status starting --pid `$PID --note `"attempt `$workflowAttempt/$MaxAttempts`" --json | Out-Null
    Add-Content -Path '$LogPath' -Value ("[{0}] attempt {1}/{2} starting" -f [DateTime]::UtcNow.ToString("o"), `$workflowAttempt, $MaxAttempts)
    `$workflowLaunchMarker = Start-Job -ScriptBlock {
        param(`$repoRoot, `$agent, `$delaySeconds, `$pidValue, `$attempt)
        Start-Sleep -Seconds `$delaySeconds
        Set-Location `$repoRoot
        poetry run python scripts/workflow_launch_state.py --repo-root `$repoRoot update --agent `$agent --status running --pid `$pidValue --note `"startup grace passed on attempt `$attempt`" --json | Out-Null
    } -ArgumentList '$RepoRoot', '$Agent', $StartupGraceSeconds, `$PID, `$workflowAttempt
    `$workflowStartTime = Get-Date
    try {
$StartupCommand
    }
    finally {
        if (`$workflowLaunchMarker) {
            Stop-Job -Job `$workflowLaunchMarker -ErrorAction SilentlyContinue | Out-Null
            Remove-Job -Job `$workflowLaunchMarker -Force -ErrorAction SilentlyContinue | Out-Null
        }
    }
    `$workflowExitCode = `$LASTEXITCODE
    if ($null -eq `$workflowExitCode) {
        `$workflowExitCode = 0
    }
    `$workflowRuntimeSeconds = ((Get-Date) - `$workflowStartTime).TotalSeconds
    Add-Content -Path '$LogPath' -Value ("[{0}] attempt {1}/{2} exited code={3} runtime_seconds={4}" -f [DateTime]::UtcNow.ToString("o"), `$workflowAttempt, $MaxAttempts, `$workflowExitCode, [Math]::Round(`$workflowRuntimeSeconds, 2))
    if (`$workflowRuntimeSeconds -ge $StartupGraceSeconds) {
        poetry run python scripts/workflow_launch_state.py --repo-root '$RepoRoot' update --agent $Agent --status exited --pid `$PID --exit-code `$workflowExitCode --note `"cli exited after running`" --json | Out-Null
        return
    }
    if (`$workflowAttempt -lt `$workflowLaunchAttempts) {
        poetry run python scripts/workflow_launch_state.py --repo-root '$RepoRoot' update --agent $Agent --status starting --pid `$PID --exit-code `$workflowExitCode --note `"retrying after quick exit on attempt `$workflowAttempt`" --json | Out-Null
        Start-Sleep -Seconds `$workflowRetryDelaySeconds
    }
    else {
        poetry run python scripts/workflow_launch_state.py --repo-root '$RepoRoot' update --agent $Agent --status exited --pid `$PID --exit-code `$workflowExitCode --note `"cli returned to powershell after retries`" --json | Out-Null
    }
}
"@
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
        $window = [WorkflowWindowLayout]::EnumerateWindows() | Where-Object { $_.Title -eq $WindowTitle } | Select-Object -First 1
        if ($null -ne $window) {
            return $window.Handle
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
    $outerPadding = 12
    $horizontalGap = 10
    $verticalGap = 10
    $maxWidth = [Math]::Floor(($bounds.Width - ($outerPadding * 2) - ($horizontalGap * ($columns - 1))) / $columns)
    $maxHeight = [Math]::Floor(($bounds.Height - ($outerPadding * 2) - ($verticalGap * ($rows - 1))) / $rows)

    for ($index = 0; $index -lt $WindowTitles.Count; $index++) {
        $handle = Get-WorkflowWindowHandle -WindowTitle $WindowTitles[$index]
        if ($handle -eq [IntPtr]::Zero) {
            continue
        }

        $column = $index % $columns
        $row = [Math]::Floor($index / $columns)
        $x = $bounds.Left + $outerPadding + ($column * ($maxWidth + $horizontalGap))
        $y = $bounds.Top + $outerPadding + ($row * ($maxHeight + $verticalGap))
        [WorkflowWindowLayout]::SetWindowPos(
            $handle,
            [IntPtr]::Zero,
            $x,
            $y,
            0,
            0,
            ($SWP_NOSIZE -bor $SWP_NOZORDER -bor $SWP_NOACTIVATE)
        ) | Out-Null
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

    if ($startupType -eq "direct_cli") {
        $command = New-DirectCliLaunchCommand -RepoRoot $mainRepo -Agent ([string]$role.agent) -StartupCommand $startupCommand -LogPath $logPath -StartupGraceSeconds $StartupGraceSeconds -MaxAttempts $maxAttempts -RetryDelaySeconds $retryDelaySeconds
    }
    elseif ($startupType -eq "audit_agent") {
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
        TitleCandidates = @($role.window_title_fallbacks | ForEach-Object { [string]$_ })
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
            Stop-WorkflowWindowsByExactTitle -WindowTitle $target.Title
            Write-LaunchState -RepoRoot $mainRepo -Agent $target.Agent -Status "starting" -Note ("attempt {0}/{1}" -f $attempt, $target.MaxAttempts)
            Add-Content -Path (Get-LaunchLogPath -RepoRoot $mainRepo -Agent $target.Agent) -Value ("[{0}] attempt {1}/{2} launching via {3}" -f [DateTime]::UtcNow.ToString("o"), $attempt, $target.MaxAttempts, $target.StartupType)
        }

        $process = Start-WorkflowWindow -WindowTitle $target.Title -Workdir $target.Workdir -CommandText $target.Command -StartupType $target.StartupType
        if (-not $DryRun -and $null -ne $process) {
            $windowInfo = Get-WindowInfoByTitleCandidates -WindowTitles $target.TitleCandidates
            if ($null -eq $windowInfo) {
                $windowInfo = Get-WindowInfoByProcessId -ProcessId $process.Id -TimeoutSeconds 2
            }
            $hwnd = if ($null -ne $windowInfo) { [Int64]$windowInfo.Handle } else { [Int64]0 }
            $windowPid = if ($null -ne $windowInfo) { [int]$windowInfo.ProcessId } else { $process.Id }
            $windowManifest[$target.Agent] = @{
                pid = $windowPid
                hwnd = $hwnd
                title = $target.Title
                workdir = $target.Workdir
            }
            Save-WindowManifest -RepoRoot $mainRepo -Windows $windowManifest

            if ($target.StartupType -eq "direct_cli" -or $target.StartupType -eq "audit_agent") {
                $health = Wait-WorkflowLaunchHealthy -RepoRoot $mainRepo -Agent $target.Agent -ProcessId $process.Id -TimeoutSeconds $StartupTimeoutSeconds
                if ($health.ok) {
                    $statePid = 0
                    if ($null -ne $health.state -and $health.state.PSObject.Properties.Name -contains "pid") {
                        $statePid = [int]$health.state.pid
                    }
                    $aliveWindow = Get-WindowInfoByTitleCandidates -WindowTitles $target.TitleCandidates -TimeoutSeconds 2
                    if ($null -eq $aliveWindow) {
                        $candidatePid = if ($statePid -gt 0) { $statePid } else { $process.Id }
                        $aliveWindow = Get-WindowInfoByProcessId -ProcessId $candidatePid -TimeoutSeconds 2
                    }
                    if ($null -eq $aliveWindow) {
                        Write-Error ("Launch failed for {0}: window_binding_missing" -f $target.Agent)
                    }
                    else {
                        $windowManifest[$target.Agent] = @{
                            pid = if ($statePid -gt 0) { $statePid } else { $process.Id }
                            hwnd = [Int64]$aliveWindow.Handle
                            title = if ([string]::IsNullOrWhiteSpace([string]$aliveWindow.Title)) { $target.Title } else { [string]$aliveWindow.Title }
                            workdir = $target.Workdir
                        }
                        Save-WindowManifest -RepoRoot $mainRepo -Windows $windowManifest
                        if (-not $SkipLayout) {
                            Set-WorkflowGridLayout -WindowTitles ($targets | ForEach-Object { $_.Title })
                        }
                        $started = $true
                    }
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
    if ($UseTerminalController) {
        $controllerCommand = "Start-Sleep -Seconds $ControllerDelaySeconds; pwsh ./scripts/workflow-terminal-control-console.ps1 -Interval $ControlInterval"
    }
    else {
        $controllerCommand = "Start-Sleep -Seconds $ControllerDelaySeconds; pwsh ./scripts/workflow-supervisor-console.ps1 -Interval $ControlInterval"
    }
    Start-WorkflowWindow -WindowTitle "owlclaw-control" -Workdir $mainRepo -CommandText $controllerCommand
}
