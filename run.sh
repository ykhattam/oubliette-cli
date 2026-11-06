#!/usr/bin/env bash
# Launcher for oubliette-cli. Works from any directory, no venv activation needed.
#   ./run.sh --file src/main.py --prompt "Review this code."
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# One audit trail regardless of which project directory you run from.
export OUBLIETTE_AUDIT_DIR="${OUBLIETTE_AUDIT_DIR:-$HOME/.local/state/oubliette}"

if [[ ! -x "$ROOT/.venv/bin/oubliette" ]]; then
  echo "[run.sh] venv entry point missing; restoring editable install..." >&2
  "$ROOT/.venv/bin/python" -m pip install -q -e "$ROOT"
fi

exec "$ROOT/.venv/bin/oubliette" "$@"
