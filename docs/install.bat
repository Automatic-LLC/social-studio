@echo off
REM Social Studio installer for a Windows PC. Double-click it. Safe to run again: it only adds what is missing,
REM then gets the newest code. Installs into C:\SocialStudio.
setlocal
title Social Studio installer
set "DIR=C:\SocialStudio"
set "REPO=https://github.com/Automatic-LLC/social-studio.git"
set "NEED_RESTART="

echo.
echo === Social Studio installer ===
echo.

where winget >nul 2>nul
if errorlevel 1 goto :nowinget

where py >nul 2>nul
if not errorlevel 1 goto :havepy
echo Installing Python...
winget install -e --id Python.Python.3.12 --scope user --accept-source-agreements --accept-package-agreements
set "NEED_RESTART=1"
:havepy

where git >nul 2>nul
if not errorlevel 1 goto :havegit
echo Installing Git...
winget install -e --id Git.Git --accept-source-agreements --accept-package-agreements
set "NEED_RESTART=1"
:havegit

where ffmpeg >nul 2>nul
if not errorlevel 1 goto :haveffmpeg
echo Installing ffmpeg (the video tool)...
winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
set "NEED_RESTART=1"
:haveffmpeg

if not defined NEED_RESTART goto :tools_ok
echo.
echo New programs were installed. Windows only sees them in a new window:
echo CLOSE this window and DOUBLE-CLICK install.bat AGAIN to finish.
echo.
pause
exit /b 0

:tools_ok
if exist "%DIR%\.git" goto :update
echo Getting the code into %DIR% ...
git clone %REPO% "%DIR%"
if errorlevel 1 goto :fail
goto :code_ok
:update
echo Getting the newest code...
cd /d "%DIR%"
git checkout main
git pull origin main
:code_ok

cd /d "%DIR%"
echo Installing the Python parts...
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
if errorlevel 1 goto :fail

if exist "%DIR%\.env" goto :env_ok
if exist "C:\Trading\SocialStudio.env" goto :env_ok
copy /y "%DIR%\.env.example" "%DIR%\.env" >nul
echo.
echo Notepad is opening your secrets file (.env). Fill in the values you have,
echo SAVE it (Ctrl+S) and CLOSE Notepad to continue. Never send this file to anyone.
start /wait notepad "%DIR%\.env"
:env_ok

echo.
echo === Checking the setup ===
py -m social_studio doctor
echo.
echo Done. From now on: double-click pull.bat in %DIR% to update, and use the commands in SETUP.md.
start "" explorer "%DIR%"
pause
exit /b 0

:nowinget
echo winget is missing. Open the Microsoft Store, install "App Installer", then run this again.
pause
exit /b 1

:fail
echo.
echo Something failed above. Take a screenshot of this window and send it to Claude.
pause
exit /b 1
