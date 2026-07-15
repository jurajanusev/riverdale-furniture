$ErrorActionPreference = "SilentlyContinue"
$project = Split-Path -Parent $MyInvocation.MyCommand.Path
$tailscaleCandidates = @(
    "C:\Program Files\Tailscale\tailscale.exe",
    "C:\Program Files (x86)\Tailscale\tailscale.exe"
)
$tailscale = $tailscaleCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($tailscale) { & $tailscale serve off }

$pidFile = Join-Path $project "data\riverdale.pid"
if (Test-Path $pidFile) {
    $serverPid = [int](Get-Content $pidFile)
    $process = Get-Process -Id $serverPid -ErrorAction SilentlyContinue
    if ($process -and $process.ProcessName -match "python") {
        Stop-Process -Id $serverPid
    }
    Remove-Item -LiteralPath $pidFile -Force
}
