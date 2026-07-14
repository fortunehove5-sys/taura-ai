#!/usr/bin/env bash
# Convenience wrapper for the CLI voice-call channel simulator.
# Usage: ./scripts/run_cli_demo.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -d ".venv" ]; then
  echo "No .venv found -- creating one and installing dependencies..."
  python3 -m venv .venv
  ./.venv/bin/pip install --quiet -r requirements.txt
fi

PYTHONPATH=src ./.venv/bin/python -m taura.channels.cli_chat
