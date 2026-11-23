# Agentic RAG Assistant on Google Cloud

Document-grounded multi-agent question answering using Google ADK, Gemini embeddings, FastAPI, and **ChromaDB locally / Firestore vector search on Google Cloud Run**.

## Architecture

1. Upload PDFs or UTF-8 text; extract text, split with overlap, embed with Gemini, and index in ChromaDB (local) or Firestore (Cloud Run).
2. ADK router decides if retrieval is needed; retrieval worker obtains similar chunks.
3. ADK answer agent cites [S1], [S2] source excerpts or abstains when documents cannot support an answer.
4. Responses expose source excerpts, retrieval distance, request latency, route, and token usage when available.

## Quickstart

Requires Python 3.11+, a Gemini Developer API key, and an API access key.

~~~bash
git clone https://github.com/BhushanVidhate-27/agentic-rag-google-cloud.git
cd agentic-rag-google-cloud
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Fill GEMINI_API_KEY and API_ACCESS_KEY
uvicorn agentic_rag.api:app --reload
~~~

Browse to http://localhost:8000 (demo) or http://localhost:8000/docs (OpenAPI).

~~~bash
curl -X POST http://localhost:8000/v1/documents -H "X-API-Key: YOUR_KEY" -F "file=@examples/handbook.txt"
curl -X POST http://localhost:8000/v1/ask -H "X-API-Key: YOUR_KEY" -H "Content-Type: application/json" -d '{"question":"Who handles P1 incidents?"}'
~~~

## Test and evaluate

~~~bash
ruff check .
pytest -q
API_ACCESS_KEY=YOUR_API_ACCESS_KEY python scripts/evaluate.py --dataset eval/sample.jsonl --base-url http://localhost:8000
~~~

Upload examples/handbook.txt before evaluation. Source-hit rate and approximate answer-substring accuracy are calculated from the supplied evaluation dataset. **No benchmark results, production deployment, operating costs, or source corpus size are claimed in advance.**

## Free public Render preview (no billing account)

The repository includes [render.yaml](render.yaml) and a [step-by-step Render deployment guide](docs/RENDER_DEMO.md). Create a **New > Blueprint** in Render, connect this repository, and confirm that the proposed Docker service uses the **Free** plan.

The preview uses a **fictional bundled handbook and deterministic keyword retrieval**, not live Gemini or ADK inference. It requires no secrets or external database. The demo is read-only; /v1 document uploads and private question-answer endpoints are disabled with DEMO_MODE=true. This makes it safe to share without exposing a Gemini API key. It is a UI and retrieval demonstration, not a measured model benchmark.

## Cloud Run deployment (no Chroma Cloud signup)

**Chroma Cloud is winding down**, so new signups are disabled. The Google Cloud Run deployment now uses **Firestore native vector search**, which has persistent storage and is managed within your existing Google Cloud project. Local development **still uses open-source ChromaDB**; no changes are required for running locally.

See **[Cloud Run + Firestore setup](docs/CLOUD_RUN_SETUP.md)** for Firestore vector index creation, Google Secret Manager configuration, IAM, short-lived GitHub Actions authentication, and the manual deployment workflow. Live deployment still requires your own Google Cloud project, Gemini Developer API key, a Firestore database, and permissions. Pushing this repository alone does not deploy anything.

The service remains private and requests require both Cloud Run IAM authorization and the X-API-Key application key.

## Security and limitations

- **Single tenant:** all uploaded documents share one corpus and API key. Add per-user authentication and tenant separation for real customers.
- Uploads are size/chunk limited; only extractable PDF text and UTF-8 TXT are supported (no OCR).
- Uploaded originals are not retained; Chroma stores embedded snippets. Re-uploading the same filename replaces its previous chunks in either backend.
- Retrieved text is treated as untrusted, but prompt injection and model errors remain possible; inspect source citations.
- Vector distance is not a calibrated confidence score. ADK sessions are ephemeral per request.
- API key is required for data endpoints; /health is publicly readable.
- Cloud services can incur charges.

## Future work

Persistent tracing, evaluation with human-rated answers, async ingestion queues, per-tenant identity, quotas, cost accounting, and optionally Vertex AI.

MIT licensed. Demo handbook is fictional.
