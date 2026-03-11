@echo off
cd /d "%~dp0"

where pyw >nul 2>&1
if %errorlevel%==0 (
    pyw -3 windows_alarm_popup.py start
    exit /b
)

where pythonw >nul 2>&1
if %errorlevel%==0 (
    pythonw windows_alarm_popup.py start
    exit /b
)

python windows_alarm_popup.py start
