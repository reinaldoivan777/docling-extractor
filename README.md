# Document RAG Processor

React + Flask scaffold for a Docling-based document ingestion and RAG chunking app.

## Backend

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

The Flask API runs on `http://localhost:5000`.
If that port is already in use, run `PORT=5001 python run.py`.

## Frontend

```sh
cd frontend
npm install
npm run dev
```

The Vite dev server runs on `http://localhost:5173`.
If the backend is using another port, run `VITE_API_PROXY_TARGET=http://localhost:5001 npm run dev`.

## Current Endpoint

```text
GET /api/health
```

Returns API health and placeholder Docling readiness.
