param(
    [string]$WindowTitle,
    [int]$ProcessId = 0
)

if (-not $WindowTitle -and $ProcessId -le 0) {
    Write-Error "Either WindowTitle or ProcessId is required"
    exit 1
}

$activated = $false
if ($ProcessId -gt 0) {
    Add-Type -AssemblyName Microsoft.VisualBasic
    try {
        [Microsoft.VisualBasic.Interaction]::AppActivate($ProcessId)
        $activated = $true
    }
    catch {
        $activated = $false
    }
}

if (-not $activated -and $WindowTitle) {
    $wshell = New-Object -ComObject WScript.Shell
    $activated = $wshell.AppActivate($WindowTitle)
}

if (-not $activated) {
    Write-Error "Window not found"
    exit 1
}

if ($ProcessId -gt 0) {
    Write-Output "focused:pid=$ProcessId"
}
else {
    Write-Output "focused:$WindowTitle"
}
