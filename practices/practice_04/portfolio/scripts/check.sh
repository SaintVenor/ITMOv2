#!/bin/sh
# Единый runner проверок проекта. Его вызывает и человек, и hook OpenCode.
set -u
cd "$(dirname "$0")/.."
python3 -m pytest -q --no-header -p no:cacheprovider -W ignore::DeprecationWarning tests
status=$?
if [ "$status" -eq 0 ]; then echo "CHECK: PASS"; else echo "CHECK: FAIL (exit $status)"; fi
exit "$status"
