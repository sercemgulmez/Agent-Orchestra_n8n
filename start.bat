@echo off
echo ======================================
echo   YemekTest Hub — Startup Script
echo ======================================

:: Copy .env if not present
if not exist .env (
    copy .env.example .env
    echo [1/5] .env created from .env.example — please fill in ANTHROPIC_API_KEY
) else (
    echo [1/5] .env already exists
)

:: Install Python dependencies
echo [2/5] Installing Python dependencies...
pip install -r requirements.txt -q

:: Build React UI
echo [3/5] Building React UI...
cd mock_ui
call npm install --silent
call npm run build --silent
cd ..

:: Start services in background
echo [4/5] Starting services...
start /B "MockAPI" uvicorn mock_api.server:app --host 0.0.0.0 --port 8001 --log-level warning
start /B "Orchestrator" uvicorn main:app --host 0.0.0.0 --port 8000 --log-level warning

:: Wait
timeout /t 4 /nobreak >nul

:: Health check
echo [5/5] Health check...
curl -sf http://localhost:8000/health >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ======================================
    echo   All services running!
    echo ======================================
    echo   Orchestrator:  http://localhost:8000
    echo   Dashboard:     http://localhost:8000/dashboard
    echo   Mock API:      http://localhost:8001
    echo ======================================
) else (
    echo ERROR: Health check failed. Services may still be starting.
    echo Try: curl http://localhost:8000/health
)
pause
