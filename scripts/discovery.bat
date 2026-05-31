@echo off
title MikaBot - Discovery
echo Starting Discovery mode...
cd /d "%~dp0.."
python src\discovery.py
pause
