#!/usr/bin/env bash
# Create a virtual environment, install dependencies from pyproject.toml, and activate it
# Usage:
#   source scripts/setup_venv.sh [extras]
# Examples:
#   source scripts/setup_venv.sh            # installs front,back,dev
#   source scripts/setup_venv.sh back       # installs only back
#   source scripts/setup_venv.sh front,dev  # installs front and dev

set -euo pipefail

EXTRAS="${1:-front,back,dev}"

if [ ! -d ".venv" ]; then
    python3.12 -m venv .venv
fi

source .venv/bin/activate

# Ensure up-to-date installer
python -m pip install --upgrade pip setuptools wheel

# Install project with selected extras from pyproject.toml
python -m pip install ".[${EXTRAS}]"

echo "Virtual environment is now active. Run 'deactivate' to exit."
