#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "========================================"
echo "  AgentNexLiFy Demo Platform"
echo "========================================"
echo ""

# Install frontend dependencies
if [ ! -d node_modules ]; then
  echo "[1/2] Installing frontend dependencies..."
  npm install --silent
else
  echo "[1/2] Frontend dependencies already installed."
fi

# Try to set up Python backend (optional)
BACKEND_PID=""
if command -v python3 &> /dev/null; then
  echo "[2/2] Setting up AI backend..."
  if python3 -c "import fastapi, uvicorn" 2>/dev/null; then
    echo "       FastAPI ready."
  else
    echo "       Installing Python dependencies..."
    pip install -r server/requirements.txt -q 2>/dev/null || pip3 install -r server/requirements.txt -q 2>/dev/null || true
  fi

  if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "       Anthropic API key detected — live AI chat enabled!"
  else
    echo "       No ANTHROPIC_API_KEY set — using simulated chat responses."
    echo "       To enable live AI: export ANTHROPIC_API_KEY=sk-ant-..."
  fi

  # Start backend in background
  python3 server/app.py &
  BACKEND_PID=$!
  echo "       Backend started on http://localhost:8000 (PID: $BACKEND_PID)"
else
  echo "[2/2] Python3 not found — skipping AI backend (chat will use simulated responses)."
fi

echo ""
echo "Starting frontend on http://localhost:3000 ..."
echo ""

# Cleanup backend on exit
cleanup() {
  if [ -n "$BACKEND_PID" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

# Start frontend
npx vite --port 3000 --open
