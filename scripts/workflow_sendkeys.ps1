param(
    [string]$WindowTitle,
    [int]$ProcessId = 0,
    [Parameter(Mandatory = $true)][string]$Message
)

$wshell = New-Object -ComObject WScript.Shell
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
    $activated = $wshell.AppActivate($WindowTitle)
}

if (-not $activated) {
    if ($ProcessId -gt 0) {
        Write-Error "Window not found: pid=$ProcessId title=$WindowTitle"
    }
    else {
        Write-Error "Window not found: $WindowTitle"
    }
    exit 1
}

Start-Sleep -Milliseconds 300
Set-Clipboard -Value $Message
Start-Sleep -Milliseconds 100
$wshell.SendKeys('^v')
Start-Sleep -Milliseconds 100
$wshell.SendKeys('~')

if ($ProcessId -gt 0) {
    Write-Output "sent:pid=${ProcessId}:$Message"
}
else {
    Write-Output "sent:${WindowTitle}:$Message"
}
