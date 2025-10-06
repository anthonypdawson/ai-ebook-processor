@echo off
REM AI Ebook Processor CLI Wrapper for Windows
REM This allows running the CLI directly from anywhere

setlocal

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."

REM Check if uv is available and use it
where uv >nul 2>nul
if %ERRORLEVEL% equ 0 (
    cd /d "%PROJECT_DIR%"
    uv run ebook-processor %*
    goto :eof
)

REM Legacy fallback for virtual environment
set "VENV_PYTHON=%PROJECT_DIR%\.venv\Scripts\python.exe"

if exist "%VENV_PYTHON%" (
    REM Use virtual environment Python
    set "PYTHONPATH=%PROJECT_DIR%;%PYTHONPATH%"
    "%VENV_PYTHON%" -m ai_ebook_processor %*
) else (
    REM Fallback to system Python
    cd /d "%PROJECT_DIR%"
    set "PYTHONPATH=%PROJECT_DIR%;%PYTHONPATH%"
    python -m ai_ebook_processor %*
)