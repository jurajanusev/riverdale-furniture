param(
    [string]$CloudUrl = "https://riverdale-furniture.onrender.com"
)

$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $project ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Virtuálne prostredie nebolo nájdené. Najprv nainštalujte aplikáciu podľa README.md."
}

$listener = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    throw "Port 5000 už používa iná lokálna aplikácia. Zastavte pôvodnú Riverdale aplikáciu a spustite zberač znova."
}

$securePassword = Read-Host "Zadajte prihlasovacie heslo cloudovej Riverdale aplikácie" -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    $env:RIVERDALE_CLOUD_URL = $CloudUrl.TrimEnd("/")
    $env:RIVERDALE_SYNC_TOKEN = $plainPassword

    $dataDir = Join-Path $project "data"
    New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
    $stdoutLog = Join-Path $dataDir "collector-server.log"
    $stderrLog = Join-Path $dataDir "collector-server-error.log"
    $process = Start-Process -FilePath $python -ArgumentList "app.py" -WorkingDirectory $project -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog

    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Milliseconds 500
        $process.Refresh()
        if ($process.HasExited) { break }
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:5000/healthz" -TimeoutSec 1
            if ($health.ok) { $ready = $true; break }
        }
        catch { }
    }
    if (-not $ready) {
        $detail = if (Test-Path -LiteralPath $stderrLog) { (Get-Content -LiteralPath $stderrLog -Raw).Trim() } else { "" }
        if (-not $process.HasExited) { Stop-Process -Id $process.Id }
        throw "Lokálny zberač sa nepodarilo spustiť. $detail"
    }
    Start-Process "http://127.0.0.1:5000"
    Write-Host "Lokálny zberač beží. CAPTCHA produkty sa odošlú do $CloudUrl."
    Write-Host "Toto okno nechajte otvorené. Zberač zastavíte klávesmi Ctrl+C."
    try {
        while (-not $process.HasExited) {
            Start-Sleep -Seconds 2
            $process.Refresh()
        }
    }
    finally {
        if (-not $process.HasExited) { Stop-Process -Id $process.Id }
    }
}
finally {
    $env:RIVERDALE_CLOUD_URL = $null
    $env:RIVERDALE_SYNC_TOKEN = $null
    $plainPassword = $null
    if ($pointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}
