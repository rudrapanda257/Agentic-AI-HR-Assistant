#!/usr/bin/env bash
set -euo pipefail

# Bootstrap the HR Agent project.
# Usage: ./bootstrap.sh

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# Create Python venv if needed.
if [ ! -d "$BACKEND_DIR/venv" ]; then
  echo "Creating Python venv in backend/venv..."
  python3 -m venv "$BACKEND_DIR/venv"
fi

# Activate venv and install backend dependencies.
source "$BACKEND_DIR/venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r "$BACKEND_DIR/requirements.txt"

# Install frontend dependencies.
cd "$FRONTEND_DIR"
npm install

echo "Bootstrap complete."
echo "Next steps:"
echo "  cp $ROOT_DIR/.env.example $ROOT_DIR/.env" \
     "and edit $ROOT_DIR/.env with your API keys and local settings."
echo "  source $BACKEND_DIR/venv/bin/activate" \
     "&& cd $BACKEND_DIR && uvicorn main:app --reload --host 0.0.0.0 --port 8000"
echo "  cd $FRONTEND_DIR && npm run dev"
