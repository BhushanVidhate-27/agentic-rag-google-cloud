"""Pure ingestion invariants; no cloud keys needed."""

import pytest

from agentic_rag.ingestion import chunk_text, extract_text, safe_filename


def test_text_extraction_and_normalization():
    assert extract_text(b"Hello\n  world", "a.txt") == "Hello world"


def test_rejects_unknown_extension():
    with pytest.raises(ValueError, match="Only"):
        extract_text(b"x", "image.png")


def test_rejects_bad_utf8():
    with pytest.raises(ValueError, match="UTF-8"):
        extract_text(b"\xff", "doc.txt")


def test_rejects_empty_and_scanned():
    with pytest.raises(ValueError, match="No extractable"):
        extract_text(b"\n  ", "empty.txt")


def test_windows_and_unix_filename():
    assert safe_filename(r"folder\reports\sample.txt") == "sample.txt"
    assert safe_filename("/tmp/sample.pdf") == "sample.pdf"


def test_chunking_overlap():
    text = " ".join(["incident"] * 130)
    chunks = chunk_text(text, size=120, overlap=30)
    assert len(chunks) > 1
    assert all(chunk.text for chunk in chunks)
    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))


def test_invalid_chunk_window():
    with pytest.raises(ValueError):
        chunk_text("hi", size=5, overlap=5)
