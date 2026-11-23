"""Firestore vector backend for Cloud Run without Chroma Cloud.

Uses the same Gemini embedder and Evidence response model as local Chroma.
Firestore index must be created separately (see docs/FIRESTORE_SETUP.md).
"""

import hashlib

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector

from agentic_rag.config import Settings
from agentic_rag.vector_store import Embedder, Evidence, GeminiEmbedder


class FirestoreStore:
    def __init__(self, settings: Settings, embedder: Embedder | None = None, collection=None):
        self.embedder = embedder or GeminiEmbedder(settings)
        self.collection = collection or firestore.Client(
            project=settings.google_cloud_project or None
        ).collection(settings.firestore_collection)

    def index(self, source: str, chunks: list[str], document_id: str) -> int:
        if not chunks:
            raise ValueError("Empty document")
        vectors = self.embedder.embed(chunks, task_type="RETRIEVAL_DOCUMENT")

        # A file replacement must not retain stale chunks from an earlier version.
        # Index content is embedded before deletion to preserve old data on embedding errors.
        existing = self.collection.where(
            filter=FieldFilter("source", "==", source)
        ).stream()
        for snapshot in existing:
            snapshot.reference.delete()

        for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
            ident = hashlib.sha256(f"{source}:{document_id}:{i}".encode()).hexdigest()
            self.collection.document(ident).set({
                "source": source,
                "chunk_index": i,
                "document_id": document_id,
                "text": chunk,
                "embedding": Vector(vector),
            })
        return len(chunks)

    def search(self, query: str, limit: int) -> list[Evidence]:
        [vector] = self.embedder.embed([query], task_type="RETRIEVAL_QUERY")
        hits = self.collection.find_nearest(
            vector_field="embedding",
            query_vector=Vector(vector),
            distance_measure=DistanceMeasure.COSINE,
            limit=limit,
            distance_result_field="vector_distance",
        ).stream()
        result = []
        for snapshot in hits:
            data = snapshot.to_dict() or {}
            result.append(Evidence(
                source=str(data.get("source", "unknown")),
                chunk_index=int(data.get("chunk_index", 0)),
                text=str(data.get("text", "")),
                distance=(
                    float(data["vector_distance"])
                    if data.get("vector_distance") is not None else None
                ),
            ))
        return result
