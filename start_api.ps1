[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path "venv\Scripts\uvicorn.exe")) {
    Write-Host "Installing dependencies, please wait..." -ForegroundColor Cyan
    python -m venv venv
    & "venv\Scripts\pip" install -r requirements.txt -q
}

Write-Host "Starting PDD BI Dashboard API on http://127.0.0.1:8000 ..." -ForegroundColor Green
& "venv\Scripts\uvicorn" api:app --host 127.0.0.1 --port 8000 --reload
