#!/usr/bin/env bash
set -euo pipefail

# Install dependencies
pip install -r requirements.txt

# Start API server in background
uvicorn MailService.api_server:app --host 127.0.0.1 --port 8000 --reload &
API_PID=$!

# Wait for API to be ready
echo "Waiting for API to become ready..."
for i in {1..30}; do
  if curl -fsS http://127.0.0.1:8000/ >/dev/null; then
    echo "API is ready."
    break
  fi
  sleep 1
done

# Run MailClient example CLI
python MailClient.py || true

# Keep server running if desired; press Ctrl+C to stop
wait ${API_PID}


