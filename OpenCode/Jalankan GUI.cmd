@echo off
setlocal
set "JIBAS_TOOL_DIR=%~dp0"
set "JIBAS_TOOL_PY=%~dp0.venv\Scripts\pythonw.exe"
if exist "%JIBAS_TOOL_PY%" goto run_python
set "JIBAS_TOOL_PY=%~dp0..\.venv\Scripts\pythonw.exe"
if exist "%JIBAS_TOOL_PY%" goto run_python
set "JIBAS_TOOL_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe"
if exist "%JIBAS_TOOL_PY%" goto run_python
start "" pyw -3 -X utf8 -c "import os,sys; sys.path.insert(0,os.environ['JIBAS_TOOL_DIR']); import gui; gui.main()"
exit /b 0
:run_python
start "" "%JIBAS_TOOL_PY%" -X utf8 -c "import os,sys; sys.path.insert(0,os.environ['JIBAS_TOOL_DIR']); import gui; gui.main()"
exit /b 0
