# DocMind — RAG-Powered Document Q&A

> Upload a PDF. Ask questions. Get answers grounded in your document — not hallucinated from general knowledge.

Built with **FastAPI + LangChain + FAISS + Groq (LLaMA 3.3 70B) + React**

---

## Features

- **RAG Pipeline** — chunks PDFs, embeds with sentence-transformers, retrieves with FAISS
- **Groq LLaMA 3.3 70B** — ultra-fast inference for answers
- **Confidence scoring** — high / medium / low based on vector similarity
- **Hallucination detection** — flags when document context is insufficient
- **Compare mode** — side-by-side RAG answer vs plain LLM (shows WHY RAG matters)
- **Source viewer** — see exactly which document chunks backed each answer
- **Streaming support** — token-by-token streaming endpoint available
- **Multi-PDF** — upload multiple PDFs; all indexed together

---

## Project Structure

```
rag-app/
├── backend/
│   ├── main.py           # FastAPI app + all endpoints
│   ├── rag_engine.py     # Core RAG logic (ingest, embed, retrieve, answer)
│   ├── requirements.txt
│   ├── render.yaml       # Render deployment config
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.js / App.css
    │   ├── components/
    │   │   ├── UploadZone.jsx
    │   │   └── ChatWindow.jsx
    │   └── utils/api.js
    ├── public/index.html
    └── package.json
```

---

## Local Setup

### 1. Backend

```bash
cd backend

# Create virtualenv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set your Groq API key
cp .env.example .env
# Edit .env → add your GROQ_API_KEY

# Run server
uvicorn main:app --reload --port 8000
```

Backend runs at: http://localhost:8000
Swagger docs: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend

npm install

# Set backend URL
cp .env.example .env
# .env already has: REACT_APP_API_URL=http://localhost:8000

npm start
```

Frontend runs at: http://localhost:3000

---

## Deployment

### Backend → Render (Free tier)

1. Push your `backend/` folder to a GitHub repo
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your repo
4. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Environment variables → Add `GROQ_API_KEY` = your key
6. Deploy → note your URL (e.g. `https://rag-qa-backend.onrender.com`)

### Frontend → Vercel

1. Push your `frontend/` folder to GitHub
2. Go to [vercel.com](https://vercel.com) → New Project → import repo
3. Framework preset: **Create React App**
4. Environment variables:
   - `REACT_APP_API_URL` = your Render backend URL
5. Deploy

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Check if docs are loaded |
| POST | /upload | Upload a PDF file |
| POST | /query | Ask a question (full response) |
| POST | /query/stream | Ask a question (streaming SSE) |
| GET | /stats | Get indexed document stats |
| DELETE | /documents | Clear all documents |

---

## How RAG Works (for interviews)

```
PDF → PyPDF → Text chunks (800 tokens, 100 overlap)
           → sentence-transformers embeddings
           → FAISS vector index

Query → embed query → cosine similarity search → top-4 chunks
      → inject chunks as context into LLM prompt
      → LLM answers ONLY from context (hallucination guardrail)
      → confidence score = avg similarity of retrieved chunks
```

**Key design decisions to explain:**
- Chose `all-MiniLM-L6-v2` over OpenAI embeddings → free, runs locally, no API cost
- FAISS over ChromaDB → better latency at small scale (< 10k chunks)
- chunk_size=800 with overlap=100 → balance between context richness and retrieval precision
- temperature=0.1 for RAG answers → deterministic, factual
- Explicit "not found" instruction → forces model to admit when context is insufficient

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Groq — LLaMA 3.3 70B Versatile |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| Vector DB | FAISS (in-memory) |
| Orchestration | LangChain |
| PDF parsing | PyPDF |
| Backend | FastAPI + Uvicorn |
| Frontend | React 18 |
| Deployment | Render (backend) + Vercel (frontend) |

---

## Resume Description

> Built a full-stack RAG-powered document Q&A system using FastAPI, LangChain, FAISS, and Groq (LLaMA 3.3 70B). Engineered an end-to-end pipeline: PDF ingestion → semantic chunking → vector embedding → similarity retrieval → grounded LLM response with hallucination detection and confidence scoring. Implemented compare mode to demonstrate RAG accuracy vs plain LLM. Deployed backend on Render and frontend on Vercel.
