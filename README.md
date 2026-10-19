# MathProblemApp

Local SPA for practicing math from open textbooks. Extracted exercises live in SQLite; chapter text is embedded in a persistent Chroma client for RAG. Chat and grading use a local Ollama model.

## Run

Install [Ollama](https://ollama.com) and pull models (optional for extracted fixture questions):

```bash
ollama pull llama3.1
ollama pull nomic-embed-text
```

Backend (from `backend/`):

Windows:

```bash
py -m venv ../.venv
..\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

MacOS/Linux:

```bash
python3 -m venv ../.venv
..\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend (from `frontend/`):

```bash
npm install
npm run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173) — Vite proxies `/api` to port 8000.

## Ingest textbooks

Add `source_url` values in `backend/textbooks.yaml`, then:

```bash
cd backend
python -m ingest.run --id openstax-calculus
```

Reload the bundled algebra fixture:

```bash
python -m ingest.run --fixture
```

