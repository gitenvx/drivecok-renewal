#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

VENV_DIR="../venv"

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating venv ..."
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

pip install --no-cache-dir -q -r requirements.txt

exec python3 promo.py
