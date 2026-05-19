@echo off
echo ============================================
echo   Math Tutor - Firewall Setup
echo   (Run once, requires admin)
echo ============================================
echo.
echo This allows phones/tablets on the same WiFi
echo to access the app via your PC's local IP.
echo.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting admin privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo Adding firewall rule for port 8501...
netsh advfirewall firewall add rule name="Math Tutor Streamlit" dir=in action=allow protocol=TCP localport=8501 >nul 2>&1
if %errorlevel%==0 (
    echo   Rule added successfully.
) else (
    echo   Rule may already exist.
)
echo.
echo Done. Mobile devices can now access:
echo   http://10.20.95.42:8501
echo.
pause
