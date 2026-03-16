@echo off
echo Starting Knowledge Base...

:: Start Docker Desktop if not running
echo Checking Docker
docker info >nul 2>&1
if errorlevel 1 (
    echo Starting Docker Desktop
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo Waiting for Docker to start
    timeout /t 15 /nobreak >nul
)

:: Start postgres container if not running
docker start kb-postgres >nul 2>&1
echo Database started.

:: Start backend
echo Starting backend
start "Backend" cmd /k "cd /d %~dp0backend && ..\venv\Scripts\activate && uvicorn main:app"

:: Wait a moment for backend to initialize
timeout /t 3 /nobreak >nul

:: Start frontend
echo Starting frontend
start "Frontend" cmd /k "cd /d %~dp0frontend-react && npm run dev"

echo.
echo Knowledge Base is starting up
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo.
pause