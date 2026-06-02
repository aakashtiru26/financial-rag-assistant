# Enterprise Financial RAG Assistant

A document question-answering assistant for financial reports and enterprise knowledge bases, built with FastAPI, LangChain, FAISS, Groq (LLM), and HuggingFace Inference API (embeddings).

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

---

## What it does

Upload PDF, DOCX, TXT, or CSV financial documents and ask natural language questions. The assistant retrieves semantically relevant chunks from your documents and generates grounded, cited answers — it will not hallucinate or answer from outside the uploaded content.

---

## Architecture

```
financial_rag_assistant/
  app/
    api/routes.py           # HTTP endpoints
    core/                   # config, logging, security, exceptions
    models/schemas.py       # Pydantic request/response models
    services/               # document parsing, chunking, FAISS, RAG
    utils/file_utils.py     # validation, checksums, storage
    main.py
  data/
    uploads/                # stored original files
    index/                  # FAISS vector index
    metadata/               # document registry (documents.json)
  tests/
  Dockerfile
  docker-compose.yml
  .env.example
  requirements.txt
```

**Indexing flow:** Upload → Store → Parse → Chunk → Embed (HuggingFace API) → FAISS index → Metadata registry

**Query flow:** Embed question → FAISS similarity search → Groq LLM (context only) → Grounded answer + citations

---

## Prerequisites

- Python 3.11+
- A [Groq API key](https://console.groq.com) (free)
- A [HuggingFace token](https://huggingface.co/settings/tokens) (free, read access)

---

## Quick start (local)

```bash
git clone https://github.com/aakashtiru26/financial-rag-assistant.git
cd financial-rag-assistant

python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # fill in your keys
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open http://localhost:8000 — API docs at http://localhost:8000/docs

---

## Quick start (Docker)

```bash
cp .env.example .env            # fill in your keys
docker-compose up -d
```

---

## Configuration

Copy `.env.example` to `.env` and set your values:

| Variable | Required | Description |
|---|---|---|
| `FIN_RAG_API_KEY` | ✅ | App authentication key — generate with `openssl rand -hex 32` |
| `GROQ_API_KEY` | ✅ | Groq API key for LLM inference |
| `FIN_RAG_HUGGINGFACE_API_TOKEN` | ✅ | HuggingFace token for embeddings |
| `FIN_RAG_CHUNK_SIZE` | — | Text chunk size, default `1200` |
| `FIN_RAG_CHUNK_OVERLAP` | — | Chunk overlap, default `180` |
| `FIN_RAG_RETRIEVAL_K` | — | Chunks retrieved per query, default `5` |
| `FIN_RAG_MAX_UPLOAD_MB` | — | Max upload size, default `50` |
| `FIN_RAG_LOG_LEVEL` | — | Logging level, default `INFO` |

---

## API endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/health` | No | Health check |
| POST | `/api/v1/documents` | Yes | Upload and index a document |
| GET | `/api/v1/documents` | Yes | List all indexed documents |
| DELETE | `/api/v1/documents/{id}` | Yes | Delete a document |
| POST | `/api/v1/documents/reindex` | Yes | Re-index all documents |
| POST | `/api/v1/query` | Yes | Ask a question |

All authenticated endpoints require header: `X-API-Key: your-key`

---

## Example usage

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Upload a document
curl -X POST "http://localhost:8000/api/v1/documents" \
  -H "X-API-Key: your-key" \
  -F "file=@./annual_report.pdf"

# Ask a question
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"question": "What were the main revenue drivers?", "top_k": 5}'
```

---

## Deployment on Render

1. Push repo to GitHub
2. Go to [render.com](https://render.com) → New → Web Service → connect repo
3. Runtime: **Docker**, branch: **main**
4. Add these environment variables in the Render dashboard:

```
FIN_RAG_APP_NAME=Enterprise Financial RAG Assistant
FIN_RAG_ENVIRONMENT=production
FIN_RAG_API_KEY=<openssl rand -hex 32>
GROQ_API_KEY=<your groq key>
FIN_RAG_HUGGINGFACE_API_TOKEN=<your hf token>
FIN_RAG_DATA_DIR=./data
FIN_RAG_UPLOAD_DIR=./data/uploads
FIN_RAG_INDEX_DIR=./data/index
FIN_RAG_METADATA_DIR=./data/metadata
```

> **Note on persistence:** Render's free tier has an ephemeral filesystem — uploaded documents and the FAISS index are lost on redeploy. To persist data, add a [Render Disk](https://render.com/docs/disks) (requires $7/month plan) and set the data dir env vars to point to the mounted path (e.g. `/data`).

---

## Tests

```bash
pytest
```

---

## Accuracy and limitations

The assistant answers **only from retrieved document context**. If uploaded documents don't contain sufficient evidence, it says so rather than guessing.

Treat all responses as document-grounded summaries only — not investment, accounting, tax, or legal advice.

---

## License

MIT
