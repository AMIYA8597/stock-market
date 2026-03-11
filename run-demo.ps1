#!/usr/bin/env pwsh
"""
Simple Windows PowerShell script to run the NeuroQuant demo server
No complex dependencies required - just Python and FastAPI
"""

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "  NeuroQuant Demo Server" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
$pythonCheck = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found. Please install Python 3.9+" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Python found: $pythonCheck" -ForegroundColor Green
Write-Host ""

# Check if venv exists, create if not
if (-not (Test-Path "venv")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate venv
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"

# Install FastAPI and uvicorn if not already installed
Write-Host "Checking dependencies..." -ForegroundColor Yellow
python -m pip install fastapi uvicorn --quiet

Write-Host ""
Write-Host "==================================" -ForegroundColor Green
Write-Host "  Starting API Server..." -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green
Write-Host ""
Write-Host "API will be available at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend Dashboard: http://localhost:8000/app" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Run the demo server
python demo_server.py
