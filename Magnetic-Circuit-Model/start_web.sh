#!/usr/bin/env bash
# Start the Python API (real models) + Vite dev server; Ctrl-C stops both.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="$HERE/../guadaloop_lev_control/.venv/bin/python3"
"$PY" "$HERE/web/api_server.py" 8765 &
API=$!
trap 'kill $API 2>/dev/null' EXIT
cd "$HERE/web"
[ -d node_modules ] || npm install
npm run dev -- --open
