"""Gemini embeddings and Chroma vector search."""

import hashlib
from dataclasses import dataclass
from typing import Protocol

import chromadb
from google import genai
from google.genai import types

from agentic_rag.config import Settings


@dataclass(frozen=True)
class Evidence:
    source: str
    chunk_index: int
    text: str
    distance: float | None


class Embedder(Protocol):
    def embed(self, texts: list[str], *, task_type: str) -> list[list[float]]: ...


class GeminiEmbedder:
    def __init__(self, settings: Settings):
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY required")
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions

    def embed(self, texts: list[str], *, task_type: str) -> list[list[float]]:
        vectors = []
        for offset in range(0, len(texts), 16):
            response = self.client.models.embed_content(
                model=self.model,
                contents=texts[offset : offset + 16],
                config=types.EmbedContentConfig(
                    task_type=task_type, output_dimensionality=self.dimensions
                ),
            )
            vectors.extend([list(item.values) for item in response.embeddings or []])
        if len(vectors) != len(texts):
            raise RuntimeError("Embedding response incomplete")
        return vectors


class ChromaStore:
    def __init__(self, settings: Settings, embedder: Embedder | None = None, collection=None):
        self.embedder = embedder or GeminiEmbedder(settings)
        if collection is not None:
            self.collection = collection
        else:
            if settings.chroma_mode == "cloud":
                if not settings.chroma_api_key:
                    raise ValueError("CHROMA_API_KEY required for cloud")
                options = {"api_key": settings.chroma_api_key}
                if settings.chroma_tenant:
                    options["tenant"] = settings.chroma_tenant
                if settings.chroma_database:
                    options["database"] = settings.chroma_database
                client = chromadb.CloudClient(**options)
            else:
                client = chromadb.PersistentClient(path=settings.chroma_path)
            self.collection = client.get_or_create_collection(
                name=settings.chroma_collection, metadata={"hnsw:space": "cosine"}
            )

    def index(self, source: str, chunks: list[str], document_id: str) -> int:
        if not chunks:
            raise ValueError("Empty document")
        vectors = self.embedder.embed(chunks, task_type="RETRIEVAL_DOCUMENT")
        ids = [
            hashlib.sha256(f"{source}:{document_id}:{i}".encode()).hexdigest()
            for i in range(len(chunks))
        ]
        metas = [
            {"source": source, "chunk_index": i, "document_id": document_id}
            for i in range(len(chunks))
        ]
        # Compute new embeddings before removing an old version.
        self.collection.delete(where={"source": source})
        for offset in range(0, len(chunks), 100):
            end = offset + 100
            self.collection.upsert(
                ids=ids[offset:end],
                documents=chunks[offset:end],
                embeddings=vectors[offset:end],
                metadatas=metas[offset:end],
            )
        return len(chunks)

    def search(self, query: str, limit: int) -> list[Evidence]:
        count = self.collection.count()
        if not count:
            return []
        [vector] = self.embedder.embed([query], task_type="RETRIEVAL_QUERY")
        result = self.collection.query(
            query_embeddings=[vector],
            n_results=min(limit, count),
            include=["documents", "metadatas", "distances"],
        )
        docs = result.get("documents", [[]])[0] or []
        metas = result.get("metadatas", [[]])[0] or []
        distances = result.get("distances", [[]])[0] or []
        return [
            Evidence(
                source=str(meta.get("source", "unknown")),
                chunk_index=int(meta.get("chunk_index", 0)),
                text=doc,
                distance=float(distances[i]) if i < len(distances) else None,
            )
            for i, (doc, meta) in enumerate(zip(docs, metas))
        ]
