#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

export OPENHARNESS_CONFIG_DIR="${OPENHARNESS_CONFIG_DIR:-/home/kiakiakia/.openharness}"
export OPENHARNESS_DATA_DIR="${OPENHARNESS_DATA_DIR:-/home/kiakiakia/.openharness/data}"
export OPENHARNESS_WEB_HOST="${OPENHARNESS_WEB_HOST:-127.0.0.1}"
export OPENHARNESS_WEB_PORT="${OPENHARNESS_WEB_PORT:-8013}"

exec .venv/bin/python scripts/web_mvp_server.py
