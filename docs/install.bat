@echo off
REM Social Studio installer for a Windows PC. Double-click it. Safe to run again: it only adds what is missing,
REM then gets the newest code. Installs into C:\SocialStudio.
setlocal
title Social Studio installer
set "DIR=C:\SocialStudio"
set "REPO=https://github.com/Automatic-LLC/social-studio.git"
REM Where winget and the usual installers put these programs, so they are found without opening a new window.
set "PATH=%ProgramFiles%\Git\cmd;%LOCALAPPDATA%\Programs\Python\Launcher;%LOCALAPPDATA%\Microsoft\WinGet\Links;%PATH%"

echo.
echo === Social Studio installer ===
echo This window stays open until you press a key, so you can read what happened.
echo.

where winget >nul 2>nul
if errorlevel 1 goto :nowinget

where py >nul 2>nul
if not errorlevel 1 goto :havepy
echo [1/3] Installing Python...
winget install -e --id Python.Python.3.12 --scope user --accept-source-agreements --accept-package-agreements
:havepy
where git >nul 2>nul
if not errorlevel 1 goto :havegit
echo [2/3] Installing Git...
winget install -e --id Git.Git --accept-source-agreements --accept-package-agreements
:havegit
where ffmpeg >nul 2>nul
if not errorlevel 1 goto :haveffmpeg
echo [3/3] Installing ffmpeg (the video tool)...
winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
:haveffmpeg

where py >nul 2>nul
if errorlevel 1 goto :restart
where git >nul 2>nul
if errorlevel 1 goto :restart
echo OK: Python and Git are ready.

if exist "%DIR%\.git" goto :update
echo.
echo Getting the code into %DIR% ...
git clone %REPO% "%DIR%"
if errorlevel 1 goto :fail
goto :code_ok
:update
echo.
echo Getting the newest code...
cd /d "%DIR%"
git checkout main
git pull origin main
:code_ok

cd /d "%DIR%"
echo.
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
where ffmpeg >nul 2>nul
if errorlevel 1 echo Note: ffmpeg is not found yet. Posting works without it; Reels need it. Run install.bat again later.
echo.
echo Done. Your files are in %DIR%. Double-click pull.bat there to update.
start "" explorer "%DIR%"
pause
exit /b 0

:restart
echo.
echo Python or Git was just installed, and Windows needs a new window to see it.
echo CLOSE this window and DOUBLE-CLICK install.bat AGAIN to finish.
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
