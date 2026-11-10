@echo off
setlocal DisableDelayedExpansion
pushd "%~dp0" || exit /b 2
if exist ".venv\Scripts\python.exe" goto venv_python
where py >nul 2>nul
if not errorlevel 1 goto launcher_python
python -m app
goto done
:venv_python
".venv\Scripts\python.exe" -m app
goto done
:launcher_python
py -3 -m app
:done
set "JIBAS_TOOL_EXIT=%errorlevel%"
popd
if not "%JIBAS_TOOL_EXIT%"=="0" pause
exit /b %JIBAS_TOOL_EXIT%
