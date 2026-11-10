@echo off
setlocal
set "JIBAS_TOOL_DIR=%~dp0"
set "JIBAS_TOOL_PY=%~dp0.venv\Scripts\python.exe"
if exist "%JIBAS_TOOL_PY%" goto local_python
set "JIBAS_TOOL_PY=%~dp0..\.venv\Scripts\python.exe"
if exist "%JIBAS_TOOL_PY%" goto local_python
set "JIBAS_TOOL_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%JIBAS_TOOL_PY%" goto local_python
py -3 -X utf8 -c "import os,sys; sys.path.insert(0,os.environ['JIBAS_TOOL_DIR']); from cli import main; raise SystemExit(main())" %*
exit /b %errorlevel%
:local_python
"%JIBAS_TOOL_PY%" -X utf8 -c "import os,sys; sys.path.insert(0,os.environ['JIBAS_TOOL_DIR']); from cli import main; raise SystemExit(main())" %*
exit /b %errorlevel%
