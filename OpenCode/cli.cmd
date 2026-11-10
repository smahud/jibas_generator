@echo off
rem JIBAS License Tool CLI Launcher
rem Uses venv Python if available, then py -3, then python from PATH

set "SCRIPT_DIR=%~dp0"
set "VENV_PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe"
set "TOOL=%SCRIPT_DIR%jibas_license_tool.py"

if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" "%TOOL%" %*
) else (
    py -3 "%TOOL%" %* 2>nul || python "%TOOL%" %*
)