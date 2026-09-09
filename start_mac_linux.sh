#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
if [ ! -f ".venv/.mip_setup_complete" ]; then
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  touch .venv/.mip_setup_complete
fi
streamlit run app.py
