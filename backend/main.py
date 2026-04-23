from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json
import os
from dotenv import load_dotenv
from rag_engine import RAGEngine

load_dotenv()

app = FastAPI(title="RAG Document Q&A API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_engine = RAGEngine()


class QueryRequest(BaseModel):
    question: str
    session_id: str = "default"
    compare_mode: bool = False


class QueryResponse(BaseModel):
    rag_answer: str
    plain_answer: str | None = None
    confidence: str
    sources: list[dict]
    is_hallucination_risk: bool
    reasoning: str


@app.get("/health")
async def health():
    return {"status": "ok", "documents_loaded": rag_engine.has_documents()}


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 10MB.")

    result = await rag_engine.ingest_pdf(contents, file.filename)
    return result


@app.post("/query", response_model=QueryResponse)
async def query_document(req: QueryRequest):
    if not rag_engine.has_documents():
        raise HTTPException(status_code=400, detail="No document uploaded yet.")

    result = await rag_engine.query(req.question, compare_mode=req.compare_mode)
    return result


@app.post("/query/stream")
async def query_stream(req: QueryRequest):
    if not rag_engine.has_documents():
        raise HTTPException(status_code=400, detail="No document uploaded yet.")

    async def event_generator():
        async for chunk in rag_engine.query_stream(req.question):
            yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.delete("/documents")
async def clear_documents():
    rag_engine.clear()
    return {"message": "All documents cleared"}


@app.get("/stats")
async def get_stats():
    return rag_engine.get_stats()
