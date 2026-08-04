param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python 3.11+ is required. Install it and run this command again."
}

if (-not (Test-Path ".venv")) {
    py -3 -m venv .venv
}

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not $SkipInstall) {
    & $Python -m pip install --upgrade pip
    & $Python -m pip install -r requirements-dev.txt
    Push-Location "CateMate-Workbench"
    corepack pnpm install --frozen-lockfile
    Pop-Location
}

& "$Root\examples\bootstrap_demo_data.ps1" -Force
& $Python scripts\check_public_repo.py
& $Python scripts\build_synthetic_demo.py
& $Python scripts\start_workbench.py
