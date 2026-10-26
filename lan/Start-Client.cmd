@echo off
cd /d "%~dp0"
if exist "..\dist\desktop\SzeroLAN-Windows.exe" (
    start "" "..\dist\desktop\SzeroLAN-Windows.exe"
    exit /b
)
py -3 desktop.py
if errorlevel 1 pause
