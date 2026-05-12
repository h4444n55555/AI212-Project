#!/usr/bin/env bash
# Create a Python 3.11 venv and install backend deps (Unix / WSL / Docker host)
set -euo pipefail

PY_BIN=python3.11
if ! command -v ${PY_BIN} &>/dev/null; then
  echo "${PY_BIN} not found. Please install Python 3.11 or adjust the script."
  exit 1
fi

${PY_BIN} -m venv .venv311
source .venv311/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "Done. Activate the venv with: source .venv311/bin/activate"
echo "Optional: to enable Ray (requires Python 3.8-3.12):"
echo "  python -m pip install 'ray[default]>=2.0.0,<3.0.0'"
