param(
    [int]$Interval = 20,
    [switch]$Json
)

$argsList = @(
    "run",
    "python",
    "scripts/workflow_terminal_control.py",
    "--interval",
    "$Interval",
    "--force"
)

if ($Json) {
    $argsList += "--json"
}

poetry @argsList
