# Deploy a safe, free Render preview

This public preview is **not a live Gemini/ADK demonstration**. It uses a fictional sample handbook, deterministic keyword retrieval, and extractive citations. It makes **no external model requests**, accepts **no uploads**, requires **no API keys**, and writes **no persistent data**.

The full private RAG system remains available locally when DEMO_MODE=false and Gemini credentials are configured.

## Steps

1. Sign up or log in at https://dashboard.render.com/.
2. Choose **New > Blueprint** and connect your GitHub account.
3. Select **BhushanVidhate-27/agentic-rag-google-cloud**.
4. Render will detect render.yaml and propose a **Free** Docker web service called agentic-rag-preview. Verify the selected plan is Free before confirming. If the Free plan is unavailable on your account, stop rather than selecting a paid plan.
5. Wait for the Docker build and health check to finish. Open the URL Render provides (usually a render.com subdomain).
6. Select a sample question to see an extractive answer and its cited excerpt.

**Do not add GEMINI_API_KEY, GOOGLE_API_KEY, API_ACCESS_KEY, CHROMA_API_KEY, or Google Cloud credentials to the public demo.** They are intentionally unnecessary.

## Security boundaries

- DEMO_MODE=true switches the home page to a public sample UI.
- POST /demo/ask only uses bundled fictional text.
- Protected /v1/documents and /v1/ask reject requests even if someone supplies an API key.
- The public demo never calls Google ADK, Gemini, Firestore, or Chroma.
- A Render Free instance can sleep after inactivity; its filesystem is ephemeral. The sample is packaged in the Docker image, so it survives restarts.
- No visitor question history is intentionally stored by the app. Render or network infrastructure may still retain operational request metadata.
- Public endpoint abuse and platform limits remain possible. Do not use this demo to collect personal information.

## Local preview without cloud credentials

~~~bash
docker build -t agentic-rag-preview .
docker run --rm -p 8080:8080 -e DEMO_MODE=true agentic-rag-preview
~~~

Open http://localhost:8080.

Or use Python:

~~~bash
pip install -e ".[dev]"
DEMO_MODE=true uvicorn agentic_rag.api:app --port 8000
~~~

Open http://localhost:8000.

## To enable real AI later

Do **not** put a real Gemini key in a publicly accessible service with unrestricted prompts. Instead, add user authentication, rate limits, per-user quotas, abuse protection, and bounded API spend. Keep all keys server-side and use persistent external vector storage if you need user uploads. Then run the private pipeline with DEMO_MODE=false.
