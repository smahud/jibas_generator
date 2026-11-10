@echo off
rem JIBAS License Tool GUI Launcher
rem Uses venv Python if available, then py -3, then python from PATH

set "SCRIPT_DIR=%~dp0"
set "VENV_PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe"
set "GUI=%SCRIPT_DIR%gui.py"

if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" "%GUI%" %*
) else (
    py -3 "%GUI%" %* 2>nul || python "%GUI%" %*
)