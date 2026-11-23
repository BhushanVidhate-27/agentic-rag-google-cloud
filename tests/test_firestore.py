"""Test Firestore vector adapter without a live project or API key."""

from agentic_rag.config import Settings
from agentic_rag.firestore_store import FirestoreStore


class FakeEmbedder:
    def embed(self, texts, *, task_type):
        return [[float(len(text)), 0.2, 0.1] for text in texts]


class FakeSnapshot:
    def __init__(self, data, reference):
        self.data = data
        self.reference = reference

    def to_dict(self):
        return self.data


class FakeDoc:
    def __init__(self, collection, ident):
        self.collection = collection
        self.ident = ident

    def set(self, data):
        self.collection.rows[self.ident] = data

    def delete(self):
        self.collection.rows.pop(self.ident, None)


class FakeQuery:
    def __init__(self, collection, source=None, limit=None):
        self.collection = collection
        self.source = source
        self.limit = limit

    def stream(self):
        rows = list(self.collection.rows.items())
        if self.source is not None:
            rows = [(key, data) for key, data in rows if data["source"] == self.source]
        if self.limit is not None:
            rows = rows[: self.limit]
        return [
            FakeSnapshot(
                {**data, "vector_distance": 0.03}, FakeDoc(self.collection, key)
            )
            for key, data in rows
        ]


class FakeCollection:
    def __init__(self):
        self.rows = {}

    def document(self, ident):
        return FakeDoc(self, ident)

    def where(self, *, filter):
        return FakeQuery(self, source=filter.value)

    def find_nearest(self, *, vector_field, query_vector, distance_measure,
                     limit, distance_result_field):
        assert vector_field == "embedding"
        assert distance_result_field == "vector_distance"
        return FakeQuery(self, limit=limit)


def test_index_search_replace():
    collection = FakeCollection()
    store = FirestoreStore(Settings(), embedder=FakeEmbedder(), collection=collection)
    assert store.index("demo.txt", ["hello", "world"], "doc-1") == 2
    assert len(collection.rows) == 2
    assert store.search("hello", 4)[0].source == "demo.txt"
    assert store.search("hello", 4)[0].distance == 0.03
    store.index("demo.txt", ["replacement"], "doc-2")
    assert len(collection.rows) == 1
    assert store.search("new", 3)[0].text == "replacement"
