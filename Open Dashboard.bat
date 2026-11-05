@echo off
rem Refresh the reel dashboard and open it in the browser
cd /d "%~dp0"
python dashboarduild.py --open
