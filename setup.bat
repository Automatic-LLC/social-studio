@echo off
REM Social Studio: install or update what the code needs. Run once per PC (again after pull.bat if requirements change).
cd /d "%~dp0"
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py -m social_studio doctor
pause
