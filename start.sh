#!/usr/bin/env bash
set -e

echo "======================================"
echo "  YemekTest Hub — Startup Script"
echo "======================================"

# Copy .env if not present
if [ ! -f .env ]; then
  cp .env.example .env
  echo "[1/5] .env created from .env.example — please fill in ANTHROPIC_API_KEY"
else
  echo "[1/5] .env already exists"
fi

# Install Python dependencies
echo "[2/5] Installing Python dependencies..."
pip install -r requirements.txt -q

# Build React UI
echo "[3/5] Building React UI..."
cd mock_ui
npm install --silent
npm run build --silent
cd ..

# Start services in background
echo "[4/5] Starting services..."
uvicorn mock_api.server:app --host 0.0.0.0 --port 8001 --log-level warning &
MOCK_API_PID=$!

uvicorn main:app --host 0.0.0.0 --port 8000 --log-level warning &
ORCHESTRATOR_PID=$!

# Wait for services to be ready
sleep 3

# Health check
echo "[5/5] Health check..."
if curl -sf http://localhost:8000/health > /dev/null; then
  echo ""
  echo "======================================"
  echo "  All services running!"
  echo "======================================"
  echo "  Orchestrator:  http://localhost:8000"
  echo "  Dashboard:     http://localhost:8000/dashboard"
  echo "  Mock API:      http://localhost:8001"
  echo "  Mock UI:       http://localhost:3000  (npm run dev)"
  echo "  n8n:           http://localhost:5678  (docker only)"
  echo "======================================"
  echo ""
  echo "Quick test:"
  echo "  curl http://localhost:8000/api/status"
  echo "  curl http://localhost:8001/health"
  echo ""
  echo "Press Ctrl+C to stop"
  wait $MOCK_API_PID $ORCHESTRATOR_PID
else
  echo "ERROR: Health check failed. Check logs above."
  kill $MOCK_API_PID $ORCHESTRATOR_PID 2>/dev/null || true
  exit 1
fi
