@echo off
setlocal DisableDelayedExpansion
rem Keep the caller's working directory so relative input paths keep working.
set "JIBAS_TOOL_DIR=%~dp0"
set "JIBAS_TOOL_CODE=import os, sys; sys.path.insert(0, os.environ['JIBAS_TOOL_DIR']); from cli import main; raise SystemExit(main())"
if exist "%JIBAS_TOOL_DIR%.venv\Scripts\python.exe" goto venv_python
where py >nul 2>nul
if not errorlevel 1 goto launcher_python
python -c "%JIBAS_TOOL_CODE%" %*
exit /b %errorlevel%
:venv_python
"%JIBAS_TOOL_DIR%.venv\Scripts\python.exe" -c "%JIBAS_TOOL_CODE%" %*
exit /b %errorlevel%
:launcher_python
py -3 -c "%JIBAS_TOOL_CODE%" %*
exit /b %errorlevel%
