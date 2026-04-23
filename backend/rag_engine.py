import os
import asyncio
import tempfile
from typing import AsyncGenerator

from groq import AsyncGroq
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a precise document Q&A assistant.
Answer questions ONLY based on the provided context chunks from the document.
If the answer is not found in the context, explicitly say: "This information is not found in the uploaded document."
Be concise, accurate, and cite which part of the document supports your answer.
Do NOT hallucinate or use outside knowledge."""

PLAIN_SYSTEM_PROMPT = """You are a helpful AI assistant. Answer the following question using your general knowledge."""


class RAGEngine:
    def __init__(self):
        self.vectorstore = None
        self.documents = []
        self.doc_metadata = []
        self.groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )

    def has_documents(self) -> bool:
        return self.vectorstore is not None

    def clear(self):
        self.vectorstore = None
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

            if self.vectorstore is None:
                self.vectorstore = await asyncio.to_thread(
                    FAISS.from_documents, chunks, self.embeddings
                )
            else:
                new_store = await asyncio.to_thread(
                    FAISS.from_documents, chunks, self.embeddings
                )
                self.vectorstore.merge_from(new_store)

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
                    "score": round(float(1 - score), 3),
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
            or avg_score < 0.3
        )

        if avg_score >= 0.6:
            confidence = "high"
        elif avg_score >= 0.4:
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