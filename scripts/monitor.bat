@echo off
title MikaBot - Monitor
echo Starting Monitor mode...
cd /d "%~dp0.."
python src\monitor.py
pause
