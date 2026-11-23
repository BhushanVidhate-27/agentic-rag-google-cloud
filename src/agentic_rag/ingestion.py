"""PDF/text extraction and overlapping chunks."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True)
class Chunk:
    text: str
    index: int


def safe_filename(filename: str) -> str:
    name = filename.replace("\\", "/").split("/")[-1]
    name = "".join(ch for ch in name if ch.isprintable() and ch not in '<>:"|?*')
    if not name or len(name) > 160:
        raise ValueError("Invalid file name")
    return name


def extract_text(payload: bytes, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".txt":
        try:
            text = payload.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("Text files must be UTF-8") from exc
    elif suffix == ".pdf":
        try:
            reader = PdfReader(BytesIO(payload), strict=False)
            if reader.is_encrypted:
                raise ValueError("Encrypted PDFs are unsupported")
            text = " ".join(page.extract_text() or "" for page in reader.pages)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("Cannot extract PDF text") from exc
    else:
        raise ValueError("Only .pdf and .txt are supported")
    text = " ".join(text.split())
    if not text:
        raise ValueError("No extractable text; scanned PDFs need OCR")
    return text


def chunk_text(text: str, size: int = 1100, overlap: int = 180) -> list[Chunk]:
    if size < 1 or not 0 <= overlap < size:
        raise ValueError("Invalid chunk parameters")
    clean = " ".join(text.split())
    output: list[Chunk] = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + size)
        if end < len(clean):
            boundary = clean.rfind(" ", start + size // 2, end)
            if boundary > start:
                end = boundary
        part = clean[start:end].strip()
        if part:
            output.append(Chunk(part, len(output)))
        if end == len(clean):
            break
        start = max(start + 1, end - overlap)
    return output
