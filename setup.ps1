# Tao moi truong ngoai OneDrive, dung kho va DSS, chay test.
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$local = Join-Path $env:LOCALAPPDATA "seller_health"
$venv = Join-Path $local ".venv"
if (-not (Test-Path (Join-Path $root "data\olist\raw\olist_orders_dataset.csv"))) {
    Write-Host "Chua co du lieu. Xem data\README.md de tai tu Kaggle."
    exit 1
}
New-Item -ItemType Directory -Force -Path $local | Out-Null
if (-not (Test-Path (Join-Path $venv "Scripts\python.exe"))) {
    python -m venv $venv
}
$py = Join-Path $venv "Scripts\python.exe"
& $py -m pip install -q -r (Join-Path $root "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Host "Cai thu vien that bai. Kiem tra Python 3.13, mang, va duong dan khong qua dai."
    exit 1
}
$env:PYTHONUTF8 = "1"
Set-Location -LiteralPath $root
& $py run_all.py
exit $LASTEXITCODE
