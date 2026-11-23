"""REST API: authenticated ingestion, retrieval, and source-aware answers."""

import hashlib
import hmac
import time
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from agentic_rag.agents import AgentPipeline
from agentic_rag.config import Settings, get_settings
from agentic_rag.ingestion import chunk_text, extract_text, safe_filename
from agentic_rag.vector_store import ChromaStore

app = FastAPI(title="Agentic RAG Assistant", version="0.1.0")


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=3000)


def require_key(
    x_api_key: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.api_access_key or not x_api_key:
        raise HTTPException(status_code=401, detail="Missing or invalid API key")
    if not hmac.compare_digest(x_api_key, settings.api_access_key):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")


def get_store(settings: Settings = Depends(get_settings)) -> ChromaStore:
    return ChromaStore(settings)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def demo_ui() -> str:
    return (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")


@app.post("/v1/documents", dependencies=[Depends(require_key)])
async def upload_document(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    store: ChromaStore = Depends(get_store),
) -> dict:
    try:
        filename = safe_filename(file.filename or "")
        # Read one extra byte to fail closed for oversized uploads.
        data = await file.read(settings.max_file_mb * 1024 * 1024 + 1)
        if len(data) > settings.max_file_mb * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large")
        text = extract_text(data, filename)
        chunks = chunk_text(text)
        if len(chunks) > settings.max_chunks_per_file:
            raise HTTPException(status_code=413, detail="Document has too many chunks")
        document_id = hashlib.sha256(data).hexdigest()
        total = store.index(filename, [chunk.text for chunk in chunks], document_id)
        return {"filename": filename, "document_id": document_id, "chunks": total}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()


@app.post("/v1/ask", dependencies=[Depends(require_key)])
async def ask(
    request: Question,
    settings: Settings = Depends(get_settings),
    store: ChromaStore = Depends(get_store),
) -> dict:
    start = time.perf_counter()
    result = await AgentPipeline(settings, store).ask(request.question)
    result["latency_ms"] = round((time.perf_counter() - start) * 1000, 2)
    return result
