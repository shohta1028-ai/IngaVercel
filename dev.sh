#!/usr/bin/env bash
# backend(FastAPI)とfrontend(Vite)を1コマンドで同時起動する。
# 使い方: ./dev.sh
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d "$ROOT_DIR/backend/.venv" ]; then
  echo "backend/.venv が見つかりません。先に以下を実行してください:"
  echo "  cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  echo "frontend/node_modules が見つかりません。先に以下を実行してください:"
  echo "  cd frontend && npm install"
  exit 1
fi

cleanup() {
  echo ""
  echo "停止しています..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

(
  cd "$ROOT_DIR/backend"
  source .venv/bin/activate
  exec uvicorn app.api.main:app --reload --port 8000
) &
BACKEND_PID=$!

(
  cd "$ROOT_DIR/frontend"
  exec npm run dev
) &
FRONTEND_PID=$!

echo "backend:  http://localhost:8000 (PID $BACKEND_PID)"
echo "frontend: http://localhost:5173 (PID $FRONTEND_PID)"
echo "Ctrl+Cで両方停止します"

wait "$BACKEND_PID" "$FRONTEND_PID"
