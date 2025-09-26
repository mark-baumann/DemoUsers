#!/usr/bin/env bash
set -euo pipefail

VENV_DIR=".venv"

# Prüfen, ob das Virtual Environment existiert, sonst erstellen
if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual Environment $VENV_DIR existiert nicht. Erstelle es..."
    python3 -m venv "$VENV_DIR"
else
    echo "Virtual Environment $VENV_DIR existiert bereits."
fi

# Aktivieren des Virtual Environments
source "$VENV_DIR/bin/activate"

# Immer pip über python -m pip verwenden
"$VENV_DIR/bin/python3" -m pip install --upgrade pip
"$VENV_DIR/bin/python3" -m pip install -r requirements.txt

# Start API server in background
"$VENV_DIR/bin/python3" -m uvicorn MailService.api_server:app --host 127.0.0.1 --port 8000 --reload &
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
"$VENV_DIR/bin/python3" MailClient.py || true

# Keep server running if desired; press Ctrl+C to stop
wait ${API_PID}
