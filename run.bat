@echo off
setlocal enabledelayedexpansion

:: Ensure we run from the directory containing this script
cd /d "%~dp0"

echo ============================================
echo   Math Tutor - Streamlit Launcher
echo ============================================
echo.

echo [1/2] Killing orphan processes on port 8501...
set found=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8501.*LISTENING"') do (
    set found=1
    echo   Killing PID %%a
    taskkill /F /PID %%a >nul 2>&1
)
if !found!==0 echo   Port 8501 is already free
echo   Done
echo.

echo [2/2] Starting Streamlit...
echo.

:: Start Streamlit in a new window (so we can wait and open browser)
start "Streamlit Server" /MIN cmd /c "python -m streamlit run app.py --server.headless true"

:: Wait for port 8501 to become available (poll up to 30 seconds)
echo   Waiting for server to be ready...
set /a count=0
:waitloop
timeout /t 1 /nobreak >nul
set /a count+=1
netstat -ano 2>nul | findstr ":8501.*LISTENING" >nul
if !errorlevel!==0 goto ready
if !count! lss 30 goto waitloop
echo   ERROR: Server did not start within 30 seconds
pause
exit /b 1

:ready
echo   Server is ready. Opening browser...
start "" http://localhost:8501
echo.
echo   If the browser does not open automatically, visit:
echo   http://localhost:8501
echo.
echo   This window will close in 3 seconds...
echo   (Use start_hidden.vbs for completely silent launch)
timeout /t 3 /nobreak >nul
exit /b 0
