@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "venv\Scripts\uvicorn.exe" (
    echo Installing dependencies, please wait...
    python -m venv venv
    venv\Scripts\pip install -r requirements.txt -q
)
echo Starting PDD BI Dashboard API on http://127.0.0.1:8000 ...
venv\Scripts\uvicorn api:app --host 127.0.0.1 --port 8000 --reload
pause
