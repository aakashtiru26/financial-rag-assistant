# Enterprise Financial RAG Assistant

A local document question-answering assistant for financial reports and enterprise knowledge bases, built with FastAPI, LangChain, FAISS, and Ollama.

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
    test_api.py
    test_chunker.py
  Dockerfile
  docker-compose.yml
  .env.example
  requirements.txt
```

**Indexing flow:** Upload → Store → Parse → Chunk → Embed (Ollama) → FAISS index → Metadata registry

**Query flow:** Embed question → FAISS similarity search → Ollama chat (context only) → Grounded answer + citations

---

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai) installed and running
- Docker + Docker Compose (for containerised run)

Pull the required models:

```bash
ollama pull llama3.2:1b
ollama pull nomic-embed-text
ollama serve
```

---

## Quick start (local)

```bash
git clone https://github.com/YOUR_USERNAME/financial-rag-assistant.git
cd financial-rag-assistant

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # then edit FIN_RAG_API_KEY
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs: http://localhost:8000/docs

---

## Quick start (Docker Compose)

```bash
cp .env.example .env               # edit FIN_RAG_API_KEY
docker-compose up -d

# Pull Ollama models inside the container (first run only)
docker-compose exec ollama ollama pull llama3.2:1b
docker-compose exec ollama ollama pull nomic-embed-text
```

> Set `FIN_RAG_OLLAMA_BASE_URL=http://ollama:11434` in `.env` when using Docker Compose.

---

## Configuration

Copy `.env.example` to `.env` and fill in your values:

| Variable | Default | Description |
|---|---|---|
| `FIN_RAG_API_KEY` | `change-me` | API authentication key — **must change** |
| `FIN_RAG_OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `FIN_RAG_OLLAMA_LLM_MODEL` | `llama3.2:1b` | LLM model name |
| `FIN_RAG_OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model name |
| `FIN_RAG_CHUNK_SIZE` | `1200` | Text chunk size (characters) |
| `FIN_RAG_CHUNK_OVERLAP` | `180` | Overlap between chunks |
| `FIN_RAG_RETRIEVAL_K` | `5` | Number of chunks retrieved per query |
| `FIN_RAG_MAX_UPLOAD_MB` | `50` | Max file upload size |
| `FIN_RAG_LOG_LEVEL` | `INFO` | Logging level |

Generate a strong API key:

```bash
openssl rand -hex 32
```

---

## API endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/health` | No | Health check |
| POST | `/api/v1/documents` | Yes | Upload and index a document |
| GET | `/api/v1/documents` | Yes | List all indexed documents |
| DELETE | `/api/v1/documents/{id}` | Yes | Delete a document and rebuild index |
| POST | `/api/v1/documents/reindex` | Yes | Re-index all stored documents |
| POST | `/api/v1/query` | Yes | Ask a question |

All authenticated endpoints require the header: `X-API-Key: your-key`

---

## Example usage

**Health check:**
```bash
curl http://localhost:8000/api/v1/health
```

**Upload a document:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents" \
  -H "X-API-Key: your-key" \
  -F "file=@./annual_report.pdf"
```

**Ask a question:**
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"question": "What were the main drivers of revenue change?", "top_k": 5}'
```

**List documents:**
```bash
curl "http://localhost:8000/api/v1/documents" -H "X-API-Key: your-key"
```

**Delete a document:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/documents/<document_id>" \
  -H "X-API-Key: your-key"
```

**Re-index all documents:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/reindex" \
  -H "X-API-Key: your-key"
```

---

## Tests

```bash
pytest
```

Tests cover API key enforcement, the public health endpoint, and citation metadata. They avoid live Ollama calls so they run fast in CI without any model dependencies.

---

## Deployment

### Render (recommended)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New → Web Service → connect repo
3. Set environment: **Docker**, branch: **main**
4. Add environment variables in the Render dashboard (never commit real secrets)
5. Every `git push` to `main` triggers an automatic redeploy

### Fly.io

```bash
fly auth login
fly launch
fly secrets set FIN_RAG_API_KEY=$(openssl rand -hex 32)
fly deploy
```

### VPS (full Ollama support)

```bash
ssh root@your-server
apt install -y docker.io docker-compose
git clone https://github.com/YOUR_USERNAME/financial-rag-assistant.git
cd financial-rag-assistant
cp .env.example .env && nano .env
docker-compose up -d
docker-compose exec ollama ollama pull llama3.2:1b
docker-compose exec ollama ollama pull nomic-embed-text
```

Use persistent volumes for `data/uploads`, `data/index`, and `data/metadata`. Put the API behind TLS (nginx + Certbot or Cloudflare) and rotate `FIN_RAG_API_KEY` regularly.

---

## Accuracy and limitations

The assistant is instructed to answer **only from retrieved document context**. If the uploaded documents do not contain sufficient evidence, it will say it does not know rather than filling gaps.

Treat all responses as document-grounded summaries only — not investment, accounting, tax, or legal advice.

---

## License

MIT# financial-rag-assistant
