@echo off
REM Wrapper script for Cell CLI compatibility on Windows

REM Handle --version flag
if "%1" == "--version" (
    python -c "from config import __version__; print(__version__)"
    exit /b 0
)

REM Change to the script's directory
cd /d %~dp0

REM User-specific development environment
set "DISABLED_TOOLS=tracer"
set "DEFAULT_MODEL=grok-code-fast"
set "CONVERSATION_TIMEOUT_HOURS=8"
set "MAX_CONVERSATION_TURNS=20"
set "LOG_LEVEL=ERROR"

REM Execute the Python server with all arguments passed through
.\.zen_venv\Scripts\python.exe server.py %*
