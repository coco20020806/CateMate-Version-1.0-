# Copy examples/processed_data into local CateMate_processeddata (skips existing files unless -Force).
param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Src = Join-Path $PSScriptRoot "processed_data"
$Dst = Join-Path $Root "CateMate_processeddata"

if (-not (Test-Path $Src)) {
    Write-Error "Missing source folder: $Src"
}

New-Item -ItemType Directory -Force -Path $Dst | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Dst "source_tables") | Out-Null

function Copy-IfAllowed {
    param([string]$RelativePath)
    $from = Join-Path $Src $RelativePath
    $to = Join-Path $Dst $RelativePath
    if (-not (Test-Path $from)) { return }
    if ((Test-Path $to) -and -not $Force) {
        Write-Host "Skip (exists): $RelativePath  (use -Force to overwrite)"
        return
    }
    $parent = Split-Path $to -Parent
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    Copy-Item -Path $from -Destination $to -Force
    Write-Host "Copied: $RelativePath"
}

Copy-IfAllowed "sph_category_tree_lookup.csv"
Copy-IfAllowed "processed_manifest.yaml"
Copy-IfAllowed "source_tables\dashboard_history.csv"
Copy-IfAllowed "source_tables\rm_raw_data.csv"

Write-Host ""
Write-Host "Done. Synthetic processed data is in: $Dst"
Write-Host "Try: python scripts/run_category_requirement_case.py examples/cases/demo_stationery_sg.yaml"
