@echo off
setlocal

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "PYTHON_EXE=%PROJECT_DIR%\.venv\Scripts\python.exe"
set "LOG_DIR=%PROJECT_DIR%\logs"
set "LOG_FILE=%LOG_DIR%\send_review_reminders.log"
set "WINDOW_MINUTES=1440"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%PYTHON_EXE%" (
  echo [%date% %time%] Python executable not found at "%PYTHON_EXE%" >> "%LOG_FILE%"
  exit /b 1
)

cd /d "%PROJECT_DIR%"
echo [%date% %time%] Starting reminder command (window=%WINDOW_MINUTES%m) >> "%LOG_FILE%"
"%PYTHON_EXE%" -u manage.py send_review_reminders --window-minutes %WINDOW_MINUTES% >> "%LOG_FILE%" 2>&1
echo [%date% %time%] Finished reminder command (exit=%errorlevel%) >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

endlocal

