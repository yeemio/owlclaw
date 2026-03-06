param(
    [Parameter(Mandatory = $true)][string]$WindowTitle,
    [Parameter(Mandatory = $true)][string]$Message
)

$wshell = New-Object -ComObject WScript.Shell
$activated = $wshell.AppActivate($WindowTitle)
if (-not $activated) {
    Write-Error "Window not found: $WindowTitle"
    exit 1
}

Start-Sleep -Milliseconds 300
Set-Clipboard -Value $Message
Start-Sleep -Milliseconds 100
$wshell.SendKeys('^v')
Start-Sleep -Milliseconds 100
$wshell.SendKeys('~')

Write-Output "sent:${WindowTitle}:$Message"
