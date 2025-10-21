@echo off
setlocal

REM Windows start script for Complete Banking Software
REM - Activates virtual environment
REM - Runs the Flask app

if "%APP_PORT%"=="" set APP_PORT=5000
if "%APP_HOST%"=="" set APP_HOST=0.0.0.0

if not exist ".venv\Scripts\activate.bat" (
  echo [!] Virtual environment not found. Run: python install.py
  exit /b 1
)

call .venv\Scripts\activate.bat
set FLASK_ENV=production
python app.py
