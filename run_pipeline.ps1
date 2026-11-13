# Mo giao dien Dagster tai http://localhost:3000 de chay va theo doi pipeline. Chay setup.ps1 mot lan truoc.
# Chay khong giao dien: .\run_pipeline.ps1 -Job dung_lai_toan_bo   (hoac -Job chay_lai_dss)
param([string]$Job = "")
$local = Join-Path $env:LOCALAPPDATA "seller_health"
$py = Join-Path $local ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Chua co moi truong. Hay chay .\setup.ps1 truoc."
    exit 1
}
# Lich su chay cua Dagster nam ngoai OneDrive, canh kho du lieu
$env:DAGSTER_HOME = Join-Path $local "dagster"
New-Item -ItemType Directory -Force -Path $env:DAGSTER_HOME | Out-Null
$cfg = Join-Path $env:DAGSTER_HOME "dagster.yaml"
if (-not (Test-Path $cfg)) {
    # Moi luc chi mot lan chay: DuckDB chi cho mot tien trinh ghi
    Set-Content -Path $cfg -Encoding utf8 -Value @"
run_queue:
  max_concurrent_runs: 1
telemetry:
  enabled: false
"@
}
$env:PYTHONUTF8 = "1"
Set-Location -LiteralPath $PSScriptRoot
$dagster = Join-Path $local ".venv\Scripts\dagster.exe"
if ($Job) {
    & $dagster job execute -m src.pipeline.definitions -j $Job
} else {
    & $dagster dev -m src.pipeline.definitions -p 3000
}
exit $LASTEXITCODE
