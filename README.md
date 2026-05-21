# HR Agent

This repository contains a full-stack HR assistant application with a Python backend and a React frontend.

## Project structure

- `backend/`: Python FastAPI backend, Gemini LLM wrapper, Google Calendar/Gmail integrations, Chroma RAG.
- `frontend/`: React + Vite user interface.
- `.env`: local environment variables (ignored by git).
- `.env.example`: example configuration template.
- `bootstrap.sh`: bootstrap script for backend and frontend dependencies.

## Setup

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit `.env` and fill in your API keys and local paths.

3. Bootstrap the project:

```bash
./bootstrap.sh
```

If the script is not executable, run:

```bash
chmod +x bootstrap.sh
./bootstrap.sh
```

## Run backend

Activate the backend virtual environment and start the FastAPI app:

```bash
source backend/venv/bin/activate
cd backend
uvicorn main:app --reload --host "$BACKEND_HOST" --port "$BACKEND_PORT"
```

## Run frontend

```bash
cd frontend
npm run dev
```

## Local Gemini shim (optional)

If you do not yet have the Gemini Flask server running, use the provided shim for local development:

```bash
cd backend
source venv/bin/activate
python gemini_shim.py
```

Then point `GEMINI_API_URL` in `.env` to `http://localhost:5000/generate`.

## Notes

- `.env` is excluded from git by `.gitignore`.
- Keep your real API keys out of source control.
