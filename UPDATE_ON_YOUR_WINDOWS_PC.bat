@echo off
REM ============================================================
REM  Automate AI — UPDATE files on YOUR Windows laptop
REM  Run this inside your existing project folder.
REM ============================================================
setlocal EnableExtensions
cd /d "%~dp0"
title Automate AI - Updating your laptop copy...
color 0B

echo.
echo  ========================================================
echo   Updating Automate AI on this PC with the latest code
echo   (open files/folders from speech + fixed UI)
echo  ========================================================
echo.

where git >nul 2>&1
if not errorlevel 1 (
  if exist ".git" (
    echo [1/4] Git repo found — pulling latest branch...
    git fetch origin
    git checkout cursor/desktop-automation-ai-a8ac 2>nul
    git pull origin cursor/desktop-automation-ai-a8ac
    if errorlevel 1 (
      echo Git pull had an issue. Trying ZIP download fallback...
      goto ZIP_UPDATE
    )
    goto AFTER_CODE
  )
)

:ZIP_UPDATE
echo [1/4] Downloading latest project ZIP from GitHub...
set "ZIP=%TEMP%\automate-ai-update.zip"
set "TMPDIR=%TEMP%\automate-ai-update-src"
set "URL=https://github.com/muneeb-267/desktop-automation-ai/archive/refs/heads/cursor/desktop-automation-ai-a8ac.zip"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "try {" ^
  "  Invoke-WebRequest -Uri '%URL%' -OutFile '%ZIP%' -UseBasicParsing;" ^
  "  if (Test-Path '%TMPDIR%') { Remove-Item -Recurse -Force '%TMPDIR%' };" ^
  "  Expand-Archive -Path '%ZIP%' -DestinationPath '%TMPDIR%' -Force;" ^
  "  $src = Get-ChildItem '%TMPDIR%' -Directory | Select-Object -First 1;" ^
  "  if (-not $src) { throw 'ZIP extract failed' };" ^
  "  Copy-Item -Path (Join-Path $src.FullName '*') -Destination '%CD%' -Recurse -Force;" ^
  "  Write-Host 'Files updated from ZIP.';" ^
  "} catch {" ^
  "  Write-Host $_.Exception.Message;" ^
  "  exit 1" ^
  "}"
if errorlevel 1 (
  echo.
  echo ERROR: Could not download update.
  echo Open this link in Chrome, extract, and replace your folder:
  echo https://github.com/muneeb-267/desktop-automation-ai/archive/refs/heads/cursor/desktop-automation-ai-a8ac.zip
  start https://github.com/muneeb-267/desktop-automation-ai/archive/refs/heads/cursor/desktop-automation-ai-a8ac.zip
  pause
  exit /b 1
)

:AFTER_CODE
echo [2/4] Ensuring virtual environment...
if not exist ".venv\Scripts\python.exe" (
  where python >nul 2>&1
  if errorlevel 1 (
    echo Python not found. Install from https://www.python.org/downloads/ ^(tick Add to PATH^)
    pause
    exit /b 1
  )
  python -m venv .venv
)
call .venv\Scripts\activate.bat

echo [3/4] Installing / refreshing packages...
python -m pip install -U pip >nul
pip install -r requirements.txt
if errorlevel 1 (
  echo Retrying essential packages...
  pip install PyYAML PyQt5 Pillow numpy pyautogui pyperclip SpeechRecognition nltk pytest
  pip install opencv-python pytesseract mss openai google-genai spacy
)
pip install -r requirements-optional.txt
if errorlevel 1 (
  echo [i] PyAudio skipped — Chrome voice still works.
)
python -m pip install PyYAML >nul 2>&1
python -m spacy download en_core_web_sm >nul 2>&1

echo [4/4] Refreshing Desktop icon + launcher...
> "%~dp0Run Automate AI.bat" (
  echo @echo off
  echo cd /d "%~dp0"
  echo call .venv\Scripts\activate.bat
  echo python main.py
  echo if errorlevel 1 pause
)
if exist "%~dp0CREATE_DESKTOP_ICON.bat" call "%~dp0CREATE_DESKTOP_ICON.bat"

echo.
echo  ========================================================
echo   UPDATE COMPLETE on this laptop
echo.
echo   Try commands like:
echo     Open Chrome
echo     Open folder Downloads
echo     Open file phase2 doc
echo     Open Muneeb report
echo     Search weather
echo  ========================================================
echo.
echo Starting Automate AI now...
start "" "%~dp0Run Automate AI.bat"
pause
