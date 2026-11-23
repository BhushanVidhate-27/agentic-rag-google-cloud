"""Deterministic fake vector tests; no remote Chroma or Gemini."""

from agentic_rag.config import Settings
from agentic_rag.vector_store import ChromaStore


class FakeEmbedder:
    def embed(self, texts, *, task_type):
        return [[float(len(text)), 0.1, 0.2] for text in texts]


class FakeCollection:
    def __init__(self):
        self.rows = {}
        self.last_query = None

    def delete(self, *, where):
        self.rows = {
            key: value for key, value in self.rows.items()
            if value[2]["source"] != where["source"]
        }

    def upsert(self, *, ids, documents, embeddings, metadatas):
        for ident, doc, vector, meta in zip(ids, documents, embeddings, metadatas):
            self.rows[ident] = (doc, vector, meta)

    def count(self):
        return len(self.rows)

    def query(self, *, query_embeddings, n_results, include):
        self.last_query = query_embeddings
        matches = list(self.rows.values())[:n_results]
        return {
            "documents": [[row[0] for row in matches]],
            "metadatas": [[row[2] for row in matches]],
            "distances": [[0.02 for _ in matches]],
        }


def test_indexes_and_cites_sources():
    collection = FakeCollection()
    store = ChromaStore(Settings(), embedder=FakeEmbedder(), collection=collection)
    assert store.index("policy.txt", ["hello", "world"], "first") == 2
    assert collection.count() == 2
    hits = store.search("hello", 2)
    assert len(hits) == 2
    assert all(hit.source == "policy.txt" for hit in hits)
    assert hits[0].distance == 0.02


def test_replaces_same_named_file():
    collection = FakeCollection()
    store = ChromaStore(Settings(), embedder=FakeEmbedder(), collection=collection)
    store.index("policy.txt", ["old", "old2"], "version1")
    store.index("policy.txt", ["new"], "version2")
    assert collection.count() == 1
    assert store.search("new", 2)[0].text == "new"


def test_empty_store_does_not_embed_query():
    store = ChromaStore(Settings(), embedder=FakeEmbedder(), collection=FakeCollection())
    assert store.search("anything", 4) == []
