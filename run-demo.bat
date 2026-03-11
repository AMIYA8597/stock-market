@echo off
REM Simple Windows batch script to run the NeuroQuant demo server
REM Edit and remove the Python comment marker ^^^^^

setlocal enabledelayedexpansion

echo.
echo ==================================
echo   NeuroQuant Demo Server
echo ==================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.9+
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo OK Python found: %PYTHON_VERSION%
echo.

REM Check if venv exists, create if not
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

REM Activate venv
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install FastAPI and uvicorn if not already installed
echo Checking dependencies...
python -m pip install fastapi uvicorn --quiet

echo.
echo ==================================
echo   Starting API Server...
echo ==================================
echo.
echo API available at: http://localhost:8000
echo Frontend Dashboard: http://localhost:8000/app
echo.
echo Press Ctrl+C to stop the server
echo.

REM Run the demo server
python demo_server.py

endlocal
