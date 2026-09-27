@echo off
title Student Project Management Portal
cd /d "%~dp0"
echo ========================================================
echo Starting Student Project Management Portal...
echo App URL: http://127.0.0.1:5001
echo ========================================================
echo.
call venv\Scripts\activate.bat
python run.py
pause
