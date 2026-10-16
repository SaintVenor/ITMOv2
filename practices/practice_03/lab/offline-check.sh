#!/usr/bin/env bash
# Offline connectivity and local model check (manual run, do NOT auto-run in CI)
# - Step 1: verify cloud access is unavailable by failing curl to https://ollama.com
# - Step 2: verify local Ollama model (itmo-agent) responds via localhost
# - Writes full outputs with timestamps to ../results/offline-check.txt (relative to this script)

set -u

# Path is resolved from the script location, so it works from any cwd (repo root, lab/, ...)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$SCRIPT_DIR/../results/offline-check.txt"
OUT_DIR="$(dirname "$OUT")"
mkdir -p "$OUT_DIR"

ts() { date --iso-8601=seconds; }
log() { printf "[%s] %s\n" "$(ts)" "$*" >> "$OUT"; }

# start fresh
: > "$OUT"

############################################
# Step 1: Cloud connectivity should fail
############################################
log "STEP 1: Cloud connectivity check (expected to FAIL)"
log "Running: curl -sS --max-time 5 https://ollama.com"

# Capture both stdout and stderr, plus exit code
CLOUD_OUTPUT="$({ curl -sS --max-time 5 "https://ollama.com"; } 2>&1)"
CLOUD_RC=$?

log "Exit code: $CLOUD_RC"
log "Output (begin)"
printf "%s\n" "$CLOUD_OUTPUT" >> "$OUT"
log "Output (end)"

if [[ $CLOUD_RC -ne 0 ]]; then
  log "Result: FAIL as expected — no cloud access (confirms offline mode)."
else
  log "WARNING: curl succeeded unexpectedly — cloud access appears available."
fi

############################################
# Step 2: Local model (Ollama) should respond
############################################
log "STEP 2: Local model generate via http://localhost:11434/api/generate"

read -r -d '' PAYLOAD <<'JSON'
{
  "model": "itmo-agent",
  "prompt": "Напиши одно короткое предложение про тестирование.",
  "options": { "num_ctx": 65536, "seed": 42 },
  "keep_alive": "1m",
  "think": false
}
JSON

log "Running: curl -sS -H 'Content-Type: application/json' -d @- http://localhost:11434/api/generate"
LOCAL_OUTPUT="$({ printf "%s" "$PAYLOAD" | curl -sS -H 'Content-Type: application/json' -d @- "http://localhost:11434/api/generate"; } 2>&1)"
LOCAL_RC=$?

log "Exit code: $LOCAL_RC"
log "Output (begin)"
printf "%s\n" "$LOCAL_OUTPUT" >> "$OUT"
log "Output (end)"

if [[ $LOCAL_RC -eq 0 ]]; then
  log "Result: SUCCESS — local model responded."
else
  log "Result: FAILURE — local model did not respond as expected."
fi

log "Done. Output saved to $OUT"
