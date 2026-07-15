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

    $process = Start-Process -FilePath $python -ArgumentList "app.py" -WorkingDirectory $project -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds 2
    $process.Refresh()
    if ($process.HasExited) {
        throw "Lokálny zberač sa nepodarilo spustiť. Skontrolujte, či je port 5000 voľný."
    }
    Start-Process "http://127.0.0.1:5000"
    Write-Host "Lokálny zberač beží. CAPTCHA produkty sa odošlú do $CloudUrl."
    Read-Host "Stlačením Enter zberač zastavíte"
    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id
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
