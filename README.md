# Agentic RAG Assistant on Google Cloud

Document-grounded multi-agent question answering using Google ADK, Gemini embeddings, ChromaDB, and FastAPI.

## Architecture

1. Upload PDFs or UTF-8 text; extract text, split with overlap, embed with Gemini, and index in Chroma.
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

## Cloud Run deployment

Use **Chroma Cloud** for durable vectors: Cloud Run local disk is ephemeral.

**Follow [the Cloud Run setup guide](docs/CLOUD_RUN_SETUP.md)** to set up your Google Cloud project, secret versions, two service accounts, and GitHub Workload Identity Federation. The repository includes a **manual** GitHub Actions workflow under **Actions > Deploy to Google Cloud Run** that deploys from main after you configure the documented repository variables.

Deployment is private and requires IAM Cloud Run Invoker **and** an X-API-Key header. The project uses a Gemini Developer API key, not Vertex AI credentials. **Pushing to GitHub does not deploy or execute a live model evaluation.**

## Security and limitations

- **Single tenant:** all uploaded documents share one corpus and API key. Add per-user authentication and tenant separation for real customers.
- Uploads are size/chunk limited; only extractable PDF text and UTF-8 TXT are supported (no OCR).
- Uploaded originals are not retained; Chroma stores embedded snippets. Re-uploading the same filename replaces its previous chunks.
- Retrieved text is treated as untrusted, but prompt injection and model errors remain possible; inspect source citations.
- Vector distance is not a calibrated confidence score. ADK sessions are ephemeral per request.
- API key is required for data endpoints; /health is publicly readable.
- Cloud services can incur charges.

## Future work

Persistent tracing, evaluation with human-rated answers, async ingestion queues, per-tenant identity, quotas, cost accounting, and optionally Vertex AI.

MIT licensed. Demo handbook is fictional.
