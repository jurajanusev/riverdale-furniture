$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $project ".venv\Scripts\python.exe"
$tailscaleCandidates = @(
    "C:\Program Files\Tailscale\tailscale.exe",
    "C:\Program Files (x86)\Tailscale\tailscale.exe"
)
$tailscale = $tailscaleCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not (Test-Path $python)) {
    throw "Chýba virtuálne prostredie .venv. Najprv dokončite inštaláciu podľa README."
}
if (-not $tailscale) {
    throw "Tailscale nie je nainštalovaný. Nainštalujte ho z https://tailscale.com/download/windows a prihláste sa."
}

$running = $false
try {
    $response = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:5000/" -TimeoutSec 2
    $running = $response.StatusCode -eq 200
} catch {}

if (-not $running) {
    $process = Start-Process -FilePath $python -ArgumentList @(
        "-m", "waitress", "--listen=127.0.0.1:5000", "app:app"
    ) -WorkingDirectory $project -WindowStyle Hidden -PassThru
    $process.Id | Set-Content -Encoding ascii (Join-Path $project "data\riverdale.pid")
    Start-Sleep -Seconds 2
}

& $tailscale serve --bg localhost:5000
& $tailscale serve status
