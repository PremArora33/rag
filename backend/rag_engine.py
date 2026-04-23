import os
import asyncio
import tempfile
import numpy as np
from typing import AsyncGenerator

from groq import AsyncGroq
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a precise document Q&A assistant.
Answer questions ONLY based on the provided context chunks from the document.
If the answer is not found in the context, explicitly say: "This information is not found in the uploaded document."
Be concise, accurate, and cite which part of the document supports your answer.
Do NOT hallucinate or use outside knowledge."""

PLAIN_SYSTEM_PROMPT = """You are a helpful AI assistant. Answer the following question using your general knowledge."""


class SimpleVectorStore:
    """Lightweight TF-IDF vector store - no external API needed."""

    def __init__(self):
        self.chunks = []
        self.vocab = {}
        self.matrix = None

    def _tokenize(self, text):
        import re
        tokens = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
        return tokens

    def _build_vocab(self):
        self.vocab = {}
        idx = 0
        for chunk in self.chunks:
            for token in set(self._tokenize(chunk.page_content)):
                if token not in self.vocab:
                    self.vocab[token] = idx
                    idx += 1

    def _vectorize(self, text):
        tokens = self._tokenize(text)
        vec = np.zeros(len(self.vocab))
        for token in tokens:
            if token in self.vocab:
                vec[self.vocab[token]] += 1
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def add_documents(self, chunks):
        self.chunks.extend(chunks)
        self._build_vocab()
        self.matrix = np.array([self._vectorize(c.page_content) for c in self.chunks])

    def similarity_search_with_score(self, query, k=4):
        if self.matrix is None or len(self.chunks) == 0:
            return []
        q_vec = self._vectorize(query)
        # Pad or trim query vector to match matrix width
        if len(q_vec) < self.matrix.shape[1]:
            q_vec = np.pad(q_vec, (0, self.matrix.shape[1] - len(q_vec)))
        else:
            q_vec = q_vec[:self.matrix.shape[1]]
        scores = self.matrix @ q_vec
        top_k = np.argsort(scores)[::-1][:k]
        return [(self.chunks[i], float(scores[i])) for i in top_k]

    def clear(self):
        self.chunks = []
        self.vocab = {}
        self.matrix = None


class RAGEngine:
    def __init__(self):
        self.vectorstore = SimpleVectorStore()
        self.documents = []
        self.doc_metadata = []
        self.groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

    def has_documents(self) -> bool:
        return len(self.documents) > 0

    def clear(self):
        self.vectorstore.clear()
        self.documents = []
        self.doc_metadata = []

    def get_stats(self) -> dict:
        return {
            "total_chunks": len(self.documents),
            "documents": self.doc_metadata,
        }

    async def ingest_pdf(self, contents: bytes, filename: str) -> dict:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            loader = PyPDFLoader(tmp_path)
            pages = loader.load()

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=800,
                chunk_overlap=100,
                separators=["\n\n", "\n", ". ", " ", ""],
            )
            chunks = splitter.split_documents(pages)

            for i, chunk in enumerate(chunks):
                chunk.metadata["chunk_id"] = i
                chunk.metadata["source_file"] = filename

            await asyncio.to_thread(self.vectorstore.add_documents, chunks)

            self.documents.extend(chunks)
            self.doc_metadata.append(
                {"filename": filename, "pages": len(pages), "chunks": len(chunks)}
            )

            return {
                "message": f"Successfully ingested '{filename}'",
                "pages": len(pages),
                "chunks": len(chunks),
            }
        finally:
            os.unlink(tmp_path)

    async def query(self, question: str, compare_mode: bool = False) -> dict:
        docs = await asyncio.to_thread(
            self.vectorstore.similarity_search_with_score, question, k=4
        )

        context_parts = []
        sources = []
        for doc, score in docs:
            context_parts.append(doc.page_content)
            sources.append(
                {
                    "text": doc.page_content[:200] + "...",
                    "page": doc.metadata.get("page", 0) + 1,
                    "score": round(float(score), 3),
                    "file": doc.metadata.get("source_file", "unknown"),
                }
            )

        context = "\n\n---\n\n".join(context_parts)
        avg_score = sum(s["score"] for s in sources) / len(sources) if sources else 0

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Context from document:\n\n{context}\n\nQuestion: {question}",
            },
        ]

        rag_response = await self.groq_client.chat.completions.create(
            model=GROQ_MODEL, messages=messages, temperature=0.1, max_tokens=1024
        )
        rag_answer = rag_response.choices[0].message.content

        is_hallucination_risk = (
            "not found" in rag_answer.lower()
            or "not mentioned" in rag_answer.lower()
            or avg_score < 0.1
        )

        if avg_score >= 0.4:
            confidence = "high"
        elif avg_score >= 0.2:
            confidence = "medium"
        else:
            confidence = "low"

        plain_answer = None
        if compare_mode:
            plain_messages = [
                {"role": "system", "content": PLAIN_SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ]
            plain_response = await self.groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=plain_messages,
                temperature=0.7,
                max_tokens=1024,
            )
            plain_answer = plain_response.choices[0].message.content

        return {
            "rag_answer": rag_answer,
            "plain_answer": plain_answer,
            "confidence": confidence,
            "sources": sources,
            "is_hallucination_risk": is_hallucination_risk,
            "reasoning": f"Retrieved {len(sources)} chunks with avg relevance score {avg_score:.2f}",
        }

    async def query_stream(self, question: str) -> AsyncGenerator[dict, None]:
        docs = await asyncio.to_thread(
            self.vectorstore.similarity_search_with_score, question, k=4
        )

        context_parts = [doc.page_content for doc, _ in docs]
        context = "\n\n---\n\n".join(context_parts)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Context from document:\n\n{context}\n\nQuestion: {question}",
            },
        ]

        stream = await self.groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=1024,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield {"type": "token", "content": delta.content}

        yield {"type": "done"}