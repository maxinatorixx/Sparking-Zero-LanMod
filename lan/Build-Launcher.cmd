@echo off
setlocal
cd /d "%~dp0"
py -3.13 -m venv .build-venv
if errorlevel 1 exit /b 1
.build-venv\Scripts\python -m pip install -r build-requirements.txt
if errorlevel 1 exit /b 1
.build-venv\Scripts\python build_desktop.py
if errorlevel 1 exit /b 1
echo Intermediate executable is in ..\.build\desktop; distribute only the full release ZIP.
