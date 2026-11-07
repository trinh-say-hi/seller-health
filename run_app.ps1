# Mo ung dung tai http://localhost:8501. Chay setup.ps1 mot lan truoc.
$py = Join-Path $env:LOCALAPPDATA "seller_health\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Chua co moi truong. Hay chay .\setup.ps1 truoc."
    exit 1
}
$env:PYTHONUTF8 = "1"
Set-Location -LiteralPath $PSScriptRoot
& $py -m streamlit run src/app/app.py @args
