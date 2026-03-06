param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("main", "review", "codex", "codex-gpt")]
    [string]$Name
)

$title = "owlclaw-$Name"
$Host.UI.RawUI.WindowTitle = $title
Write-Output "title-set:$title"
