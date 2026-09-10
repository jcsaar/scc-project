#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-5173}
RUN_MODE=${1:-serve}
RUN_LOGS=$(mktemp -d "${TMPDIR:-/tmp}/trustsplit-demo.XXXXXX")
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  if [ -n "$FRONTEND_PID" ]; then kill "$FRONTEND_PID" 2>/dev/null || true; fi
  if [ -n "$BACKEND_PID" ]; then kill "$BACKEND_PID" 2>/dev/null || true; fi
  wait "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" 2>/dev/null || true
  rm -rf "$RUN_LOGS"
}
trap cleanup EXIT INT TERM

cd "$PROJECT_ROOT/backend"
TRUSTSPLIT_DATABASE_URL=sqlite:///trustsplit.db \
  "$PROJECT_ROOT/backend/.venv/bin/alembic" upgrade head \
  >"$RUN_LOGS/migration.log" 2>&1
TRUSTSPLIT_DATABASE_URL=sqlite:///trustsplit.db \
  "$PROJECT_ROOT/backend/.venv/bin/python" -m uvicorn app.main:app \
  --host 127.0.0.1 --port "$BACKEND_PORT" >"$RUN_LOGS/backend.log" 2>&1 &
BACKEND_PID=$!

cd "$PROJECT_ROOT/frontend"
npm run dev -- --host 127.0.0.1 --port "$FRONTEND_PORT" \
  >"$RUN_LOGS/frontend.log" 2>&1 &
FRONTEND_PID=$!

wait_for_url() {
  label=$1
  url=$2
  log_file=$3
  attempt=0
  while [ "$attempt" -lt 60 ]; do
    if curl --fail --silent "$url" >/dev/null 2>&1; then
      echo "$label ready: $url"
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 0.2
  done
  echo "$label failed to start" >&2
  sed -n '1,120p' "$log_file" >&2
  return 1
}

wait_for_url "Backend" "http://127.0.0.1:$BACKEND_PORT/api/health" "$RUN_LOGS/backend.log"
wait_for_url "Dashboard" "http://127.0.0.1:$FRONTEND_PORT" "$RUN_LOGS/frontend.log"

if [ "$RUN_MODE" = "--smoke" ]; then
  exit 0
fi

echo "TrustSplit AI is running offline. Press Ctrl-C to stop."
wait "$BACKEND_PID" "$FRONTEND_PID"
