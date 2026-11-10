@echo off
setlocal
rem NOTE: this python runtime silently refuses to run a quoted script path
rem that contains spaces, so the tool is loaded as a module via -c instead.
set "JIBAS_TOOL_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe"
if exist "%JIBAS_TOOL_PY%" goto local_python
start "" pyw -3 -c "import sys; sys.path.insert(0, r'%~dp0.'); import app; app.main()"
exit /b 0
:local_python
start "" "%JIBAS_TOOL_PY%" -c "import sys; sys.path.insert(0, r'%~dp0.'); import app; app.main()"
exit /b 0
