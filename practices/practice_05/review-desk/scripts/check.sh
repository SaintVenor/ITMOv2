#!/bin/sh
# Единая команда проверки проекта.
cd "$(dirname "$0")/.." || exit 1

if [ -x .venv/bin/python ]; then
    PY=.venv/bin/python
else
    PY=python3
fi

"$PY" -m pytest -q
code=$?

if [ "$code" -eq 0 ]; then
    echo "CHECK: PASS"
else
    echo "CHECK: FAIL (exit $code)"
fi
exit "$code"
