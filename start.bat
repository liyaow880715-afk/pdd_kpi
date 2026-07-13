@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "venv\Scripts\streamlit.exe" (
    echo Installing dependencies, please wait...
    python -m venv venv
    venv\Scripts\pip install -r requirements.txt -q
)
echo Starting PDD BI Dashboard...
venv\Scripts\streamlit run app.py
pause
