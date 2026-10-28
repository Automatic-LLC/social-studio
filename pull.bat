@echo off
REM Social Studio: get the newest code from GitHub (main only).
cd /d "%~dp0"
git checkout main
git pull origin main
py -m pip install -q -r requirements.txt
pause
