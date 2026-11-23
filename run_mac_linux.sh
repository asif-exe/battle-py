#!/usr/bin/env sh
cd "$(dirname "$0")" || exit 1
python3 -u main.py
code=$?
if [ "$code" -ne 0 ]; then
    echo "BATTLE-PY exited with code $code. See battle-py-error.log if present."
fi
exit "$code"
