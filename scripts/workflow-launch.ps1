param(
    [string]$MainRepo = "D:\AI\owlclaw",
    [string]$ReviewRepo = "D:\AI\owlclaw-review",
    [string]$CodexRepo = "D:\AI\owlclaw-codex",
    [string]$CodexGptRepo = "D:\AI\owlclaw-codex-gpt",
    [string]$AuditARepo = "D:\AI\owlclaw",
    [string]$AuditBRepo = "D:\AI\owlclaw",
    [int]$ControllerDelaySeconds = 6,
    [int]$ControlInterval = 20,
    [switch]$SkipController,
    [switch]$DryRun
)

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
\$Host.UI.RawUI.WindowTitle = '$WindowTitle'
$CommandText
"@

    if ($DryRun) {
        Write-Output ("launch:{0}:{1}:{2}" -f $WindowTitle, $Workdir, $CommandText)
        return
    }

    $encoded = New-EncodedCommand -ScriptText $script
    Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoExit", "-EncodedCommand", $encoded) | Out-Null
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

if (-not $SkipController) {
    $controllerCommand = "Start-Sleep -Seconds $ControllerDelaySeconds; pwsh ./scripts/workflow-terminal-control-console.ps1 -Interval $ControlInterval"
    Start-WorkflowWindow -WindowTitle "owlclaw-control" -Workdir $MainRepo -CommandText $controllerCommand
}
