#!/usr/bin/env bash
# Create a virtual environment, install dependencies, and activate it
# Usage: source scripts/setup_venv.sh

set -e

if [ ! -d ".venv" ]; then
    python3.12 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt

echo "Virtual environment is now active. Run 'deactivate' to exit."
