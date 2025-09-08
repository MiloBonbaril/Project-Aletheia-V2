@echo off
REM Create a virtual environment, install dependencies, and activate it
REM Usage: call scripts\setup_venv.bat

if not exist .venv (
    python -m venv .venv
)

call .\.venv\Scripts\activate
pip install -r requirements.txt

echo Virtual environment is now active. Run "deactivate" to exit.
