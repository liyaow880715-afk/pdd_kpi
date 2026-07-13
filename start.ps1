[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path "venv\Scripts\streamlit.exe")) {
    Write-Host "Installing dependencies, please wait..." -ForegroundColor Cyan
    python -m venv venv
    & "venv\Scripts\pip" install -r requirements.txt -q
}

Write-Host "Starting PDD BI Dashboard..." -ForegroundColor Green
& "venv\Scripts\streamlit" run app.py
