param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 5000,
    [switch]$Install
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ApiRoot = Join-Path $ProjectRoot "smishing_detector"
$VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    $Python = $VenvPython
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $Python = "py"
} else {
    $Python = "python"
}

if ($Install) {
    & $Python -m pip install -r (Join-Path $ApiRoot "requirements.txt")
}

$env:SCAMSHIELD_HOST = $HostAddress
$env:SCAMSHIELD_PORT = [string]$Port
$env:SCAMSHIELD_DEBUG = "false"

Write-Host "Starting ScamShield Flask API at http://${HostAddress}:${Port}"
Write-Host "Health check: http://${HostAddress}:${Port}/health"
Set-Location $ApiRoot
& $Python -m app.flask_api
