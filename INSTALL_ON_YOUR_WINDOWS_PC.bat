@echo off
REM ============================================================
REM  Automate AI — ONE-CLICK install for YOUR Windows PC
REM  Double-click this file after downloading the project folder.
REM ============================================================
setlocal EnableExtensions
cd /d "%~dp0"

title Automate AI - Installing on your PC...
color 0A
echo.
echo  ========================================================
echo   Automate AI / AI Desktop Automation
echo   Installing on THIS Windows computer...
echo  ========================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [!] Python was not found on PATH.
  echo     Trying to install Python 3.12 with winget...
  where winget >nul 2>&1
  if errorlevel 1 (
    echo.
    echo ERROR: Install Python first:
    echo   1. Open https://www.python.org/downloads/
    echo   2. Download Python 3.12+
    echo   3. IMPORTANT: tick "Add python.exe to PATH"
    echo   4. Install, then double-click this file again.
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
  )
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  echo.
  echo Close this window, open a NEW Command Prompt, then run this file again.
  pause
  exit /b 1
)

echo [1/5] Python found
python --version

echo [2/5] Creating virtual environment (.venv)
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
)
call .venv\Scripts\activate.bat

echo [3/5] Installing packages (this can take a few minutes)...
python -m pip install -U pip
pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Package install had errors. If PyAudio failed, the app can still use Chrome voice.
)

echo [4/5] Downloading NLP model + preparing folders/database...
python -m spacy download en_core_web_sm >nul 2>&1
python -c "import nltk; [nltk.download(p, quiet=True) for p in ('punkt','punkt_tab','averaged_perceptron_tagger','averaged_perceptron_tagger_eng')]" 2>nul
if not exist data\captures mkdir data\captures
if not exist data\logs mkdir data\logs
if not exist assets\templates mkdir assets\templates
python -c "from src.config import load_config, ensure_runtime_dirs, resolve_path; from src.db.database import get_database; from src.vision.templates_seed import ensure_template_assets; c=load_config(); ensure_runtime_dirs(c); ensure_template_assets(resolve_path(c['paths']['templates_dir'])); get_database(c); print('Database ready')"

echo [5/5] Creating Desktop shortcut...
> "%~dp0Run Automate AI.bat" (
  echo @echo off
  echo cd /d "%~dp0"
  echo if not exist ".venv\Scripts\activate.bat" ^(
  echo   echo Run INSTALL_ON_YOUR_WINDOWS_PC.bat first.
  echo   pause
  echo   exit /b 1
  echo ^)
  echo call .venv\Scripts\activate.bat
  echo python main.py
  echo if errorlevel 1 pause
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$desk=[Environment]::GetFolderPath('Desktop');" ^
  "$ws=New-Object -ComObject WScript.Shell;" ^
  "$sc=$ws.CreateShortcut((Join-Path $desk 'Automate AI.lnk'));" ^
  "$sc.TargetPath='%~dp0Run Automate AI.bat';" ^
  "$sc.WorkingDirectory='%~dp0';" ^
  "$sc.WindowStyle=1;" ^
  "$sc.Description='AI Desktop Automation';" ^
  "$sc.Save();" ^
  "Write-Host ('Shortcut: ' + (Join-Path $desk 'Automate AI.lnk'))"

echo.
echo  ========================================================
echo   INSTALL COMPLETE
echo.
echo   On your Desktop you should now see:  Automate AI
echo.
echo   1. Double-click "Automate AI" on the Desktop
echo   2. Click "Sign Up Now" with YOUR username + password
echo   3. No demo account
echo  ========================================================
echo.
echo Starting Automate AI now...
start "" "%~dp0Run Automate AI.bat"
pause
