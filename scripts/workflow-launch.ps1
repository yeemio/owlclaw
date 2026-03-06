param(
    [string]$MainRepo = "D:\AI\owlclaw",
    [string]$ReviewRepo = "D:\AI\owlclaw-review",
    [string]$CodexRepo = "D:\AI\owlclaw-codex",
    [string]$CodexGptRepo = "D:\AI\owlclaw-codex-gpt",
    [string]$AuditARepo = "D:\AI\owlclaw",
    [string]$AuditBRepo = "D:\AI\owlclaw",
    [int]$ControllerDelaySeconds = 6,
    [int]$ControlInterval = 20,
    [int]$LayoutDelaySeconds = 8,
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
        return
    }

    $encoded = New-EncodedCommand -ScriptText $script
    $wt = Get-Command "wt.exe" -ErrorAction SilentlyContinue
    if ($null -ne $wt) {
        Start-Process -FilePath $wt.Source -ArgumentList @(
            "-w",
            "new",
            "--title",
            $WindowTitle,
            "powershell.exe",
            "-NoExit",
            "-EncodedCommand",
            $encoded
        ) | Out-Null
        return
    }

    Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoExit", "-EncodedCommand", $encoded) | Out-Null
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

$targets = @(
    @{ Title = "owlclaw-main"; Workdir = $MainRepo; Command = "codex" },
    @{ Title = "owlclaw-review"; Workdir = $ReviewRepo; Command = "claude" },
    @{ Title = "owlclaw-codex"; Workdir = $CodexRepo; Command = "agent" },
    @{ Title = "owlclaw-codex-gpt"; Workdir = $CodexGptRepo; Command = "agent" },
    @{ Title = "owlclaw-audit-a"; Workdir = $AuditARepo; Command = "agent" },
    @{ Title = "owlclaw-audit-b"; Workdir = $AuditBRepo; Command = "agent" }
)

foreach ($target in $targets) {
    Start-WorkflowWindow -WindowTitle $target.Title -Workdir $target.Workdir -CommandText $target.Command
}

if (-not $SkipLayout -and -not $DryRun) {
    Start-Sleep -Seconds $LayoutDelaySeconds
    Set-WorkflowGridLayout -WindowTitles ($targets | ForEach-Object { $_.Title })
}

if (-not $SkipController) {
    $controllerCommand = "Start-Sleep -Seconds $ControllerDelaySeconds; pwsh ./scripts/workflow-terminal-control-console.ps1 -Interval $ControlInterval"
    Start-WorkflowWindow -WindowTitle "owlclaw-control" -Workdir $MainRepo -CommandText $controllerCommand
}
