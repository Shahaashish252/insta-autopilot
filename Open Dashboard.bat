@echo off
rem Reel dashboard: opens in the browser and stays live (refreshes every minute). Close this window to stop.
cd /d "%~dp0"
python dashboard\build.py --open --watch
