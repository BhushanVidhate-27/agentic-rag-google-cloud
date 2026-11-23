#!/usr/bin/env bash
set -euo pipefail

: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
: "${CHROMA_TENANT:?Set CHROMA_TENANT}"
: "${CHROMA_DATABASE:?Set CHROMA_DATABASE}"
: "${RUNTIME_SERVICE_ACCOUNT:?Set RUNTIME_SERVICE_ACCOUNT}"

REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-agentic-rag-assistant}"

# Cloud Run source deploy uses Secret Manager references, not plaintext keys.
# Runtime service account needs secretmanager.secretAccessor on each secret.
# This service is private; access requires Cloud Run IAM and X-API-Key.
gcloud run deploy "$SERVICE" \
  --project "$GOOGLE_CLOUD_PROJECT" \
  --region "$REGION" \
  --source . \
  --service-account "$RUNTIME_SERVICE_ACCOUNT" \
  --no-allow-unauthenticated \
  --set-env-vars "CHROMA_MODE=cloud,CHROMA_TENANT=$CHROMA_TENANT,CHROMA_DATABASE=$CHROMA_DATABASE,GOOGLE_GENAI_USE_VERTEXAI=FALSE" \
  --set-secrets "GEMINI_API_KEY=gemini-api-key:latest,GOOGLE_API_KEY=gemini-api-key:latest,CHROMA_API_KEY=chroma-api-key:latest,API_ACCESS_KEY=rag-api-access-key:latest" \
  --memory 1Gi \
  --concurrency 8 \
  --min-instances 0 \
  --max-instances 2 \
  --timeout 300
