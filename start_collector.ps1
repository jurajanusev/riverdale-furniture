param(
    [string]$CloudUrl = "https://riverdale-furniture.onrender.com"
)

$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $project ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Virtualne prostredie nebolo najdene. Najprv nainstalujte aplikaciu podla README.md."
}

$listener = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    $riverdaleRunning = $false
    try {
        $existingPage = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:5000/" -TimeoutSec 3
        $riverdaleRunning = $existingPage.Content -match "<title>Riverdale Product Finder</title>"
    }
    catch { }
    if (-not $riverdaleRunning) {
        throw "Port 5000 pouziva ina aplikacia. Zastavte ju a spustite zberac znova."
    }
    Write-Host "Nasla sa starsia lokalna Riverdale. Zastavujem ju..."
    $listener.OwningProcess | Sort-Object -Unique | ForEach-Object {
        Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
    }
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        Start-Sleep -Milliseconds 250
        if (-not (Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue)) { break }
    }
    if (Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue) {
        throw "Starsiu Riverdale sa nepodarilo zastavit. Zatvorte jej terminal a skuste to znova."
    }
}

Write-Host "Teraz zadajte NOVE prihlasovacie heslo cloudovej Riverdale aplikacie. Znaky sa nebudu zobrazovat."
$securePassword = Read-Host "Heslo" -AsSecureString
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
        throw "Lokalny zberac sa nepodarilo spustit. $detail"
    }
    Write-Host "Lokalny zberac bezi. CAPTCHA produkty sa odoslu do $CloudUrl."
    Write-Host "PowerShell mozte zavriet. CAPTCHA ovladajte priamo z cloudovej Riverdale."
}
finally {
    $env:RIVERDALE_CLOUD_URL = $null
    $env:RIVERDALE_SYNC_TOKEN = $null
    $plainPassword = $null
    if ($pointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}
