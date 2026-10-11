@echo off
REM CompileX - drop and recreate all database tables, then start the stack.
setlocal
cd /d "%~dp0.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No virtualenv found at .venv - see scripts\start.bat for setup steps.
    pause
    exit /b 1
)

echo Resetting database...
pushd backend
"%CD%\..\.venv\Scripts\python.exe" reset_db.py
set RESET_FAILED=%ERRORLEVEL%
popd

if not "%RESET_FAILED%"=="0" (
    echo [ERROR] Database reset failed or was cancelled.
    pause
    exit /b 1
)

echo.
echo Database reset. Starting services...
call "%~dp0start.bat"
endlocal
