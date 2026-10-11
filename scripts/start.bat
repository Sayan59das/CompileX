@echo off
REM CompileX - start the full local stack (backend, question service, frontend)
setlocal
cd /d "%~dp0.."

REM PYTHONUTF8 is required on Windows: the services log non-ASCII characters and
REM the default cp1252 console encoding makes them crash mid-request.
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No virtualenv found at .venv
    echo Create one with:  py -3.10 -m venv .venv
    echo Then install:     .venv\Scripts\python -m pip install -r backend\requirements.txt -r question-service\requirements.txt
    pause
    exit /b 1
)

if not exist "frontend\node_modules" (
    echo [ERROR] Frontend dependencies are not installed.
    echo Run:  cd frontend ^&^& npm install
    pause
    exit /b 1
)

if not exist "backend\.env" (
    echo [WARN] backend\.env not found - copying from .env.example
    copy "backend\.env.example" "backend\.env" >nul
    echo [WARN] Set SECRET_KEY in backend\.env before using this for anything real.
)

set PY=%CD%\.venv\Scripts\python.exe

echo [1/3] Backend API      -^> http://localhost:8000
start "CompileX Backend" cmd /k "cd /d %CD%\backend && "%PY%" -m uvicorn app.main:app --reload --port 8000"

echo [2/3] Question Service -^> http://localhost:8001
start "CompileX Question Service" cmd /k "cd /d %CD%\question-service && "%PY%" -m uvicorn main_dynamic:app --reload --port 8001"

echo [3/3] Frontend         -^> http://localhost:5173
start "CompileX Frontend" cmd /k "cd /d %CD%\frontend && npm run dev"

echo.
echo All three services are starting in separate windows.
echo Open http://localhost:5173 once the frontend finishes building.
echo.
echo Press any key to stop all of them...
pause >nul

taskkill /FI "WindowTitle eq CompileX Backend*" /T /F >nul 2>&1
taskkill /FI "WindowTitle eq CompileX Question Service*" /T /F >nul 2>&1
taskkill /FI "WindowTitle eq CompileX Frontend*" /T /F >nul 2>&1
echo All services stopped.
endlocal
