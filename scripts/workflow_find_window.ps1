param(
    [Parameter(Mandatory = $true)]
    [string[]]$WindowTitles
)

Add-Type @"
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;

public static class WorkflowWindowFinder
{
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern int GetWindowTextLength(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
}
"@

$targets = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($title in $WindowTitles) {
    if ($title) {
        [void]$targets.Add($title)
    }
}

$match = $null
[WorkflowWindowFinder]::EnumWindows({
    param($hWnd, $lParam)

    if (-not [WorkflowWindowFinder]::IsWindowVisible($hWnd)) {
        return $true
    }

    $length = [WorkflowWindowFinder]::GetWindowTextLength($hWnd)
    if ($length -le 0) {
        return $true
    }

    $builder = New-Object System.Text.StringBuilder ($length + 1)
    [void][WorkflowWindowFinder]::GetWindowText($hWnd, $builder, $builder.Capacity)
    $title = $builder.ToString()
    if (-not $targets.Contains($title)) {
        return $true
    }

    [uint32]$pid = 0
    [void][WorkflowWindowFinder]::GetWindowThreadProcessId($hWnd, [ref]$pid)
    $script:match = [pscustomobject]@{
        title = $title
        hwnd = [int64]$hWnd
        pid = [int]$pid
    }
    return $false
}, [IntPtr]::Zero) | Out-Null

if ($null -eq $match) {
    [pscustomobject]@{
        found = $false
        title = ""
        hwnd = 0
        pid = 0
    } | ConvertTo-Json -Depth 3
    exit 1
}

[pscustomobject]@{
    found = $true
    title = $match.title
    hwnd = $match.hwnd
    pid = $match.pid
} | ConvertTo-Json -Depth 3
