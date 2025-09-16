@echo off
REM Create a virtual environment, install dependencies from pyproject.toml, and activate it
REM Usage:
REM   call scripts\setup_venv.bat [extras]
REM Examples:
REM   call scripts\setup_venv.bat                (installs front,back,dev)
REM   call scripts\setup_venv.bat back           (installs back)
REM   call scripts\setup_venv.bat front,dev      (installs front and dev)

setlocal enabledelayedexpansion

set EXTRAS=%1
if "%EXTRAS%"=="" (
    set EXTRAS=front,back,dev
)

if not exist .venv (
    python3.12 -m venv .venv
)

call .\.venv\Scripts\activate

REM Ensure up-to-date installer
python -m pip install --upgrade pip setuptools wheel

REM Install project with selected extras from pyproject.toml
python -m pip install ".[%EXTRAS%]"

echo Virtual environment is now active. Run "deactivate" to exit.
endlocal
