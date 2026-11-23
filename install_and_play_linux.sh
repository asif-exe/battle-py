#!/usr/bin/env bash
# First-time Linux setup; no sudo or global pip changes required.
set -e
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo 'Python 3 is required.'; exit 1; }
if [ ! -x .venv/bin/python ]; then
    echo '[BATTLE-PY] Creating an isolated Python environment...'
    python3 -m venv .venv || {
        echo 'Could not create a virtual environment. On Ubuntu/Debian install python3-venv.'
        exit 1
    }
fi
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py --self-check
printf '\n[BATTLE-PY] Press Q at any time to quit.\n'
.venv/bin/python -u main.py
