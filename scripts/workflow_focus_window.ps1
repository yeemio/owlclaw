param(
    [Parameter(Mandatory = $true)]
    [string]$WindowTitle
)

$wshell = New-Object -ComObject WScript.Shell
$activated = $wshell.AppActivate($WindowTitle)
if (-not $activated) {
    Write-Error "Window not found: $WindowTitle"
    exit 1
}

Write-Output "focused:$WindowTitle"
