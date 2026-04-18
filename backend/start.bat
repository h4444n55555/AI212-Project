@echo off
echo ----------------------------------------------------
echo Starting Object Detection OR-Tools Cluster...
echo ----------------------------------------------------
cd /d "%~dp0"

IF NOT EXIST ".venv" (
    echo 0. Creating isolated Python Virtual Environment...
    python -m venv .venv
)

echo Activating Virtual Environment...
call .venv\Scripts\activate.bat

echo Installing dependencies (this may take a minute on the first run)...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

echo 1. Booting Worker Actors (Ports 8001-8004)...
:: Using "python -m uvicorn" secures the exact venv binary
start /B python -m uvicorn main:app --port 8001 --log-level critical
start /B python -m uvicorn main:app --port 8002 --log-level critical
start /B python -m uvicorn main:app --port 8003 --log-level critical
start /B python -m uvicorn main:app --port 8004 --log-level critical

timeout /T 2 /NOBREAK > nul

echo 2. Booting Primary Edge Router (Port 8000)...
start /B python -m uvicorn router:app --port 8000

echo.
echo Cluster successfully booted! The API is live at http://127.0.0.1:8000
