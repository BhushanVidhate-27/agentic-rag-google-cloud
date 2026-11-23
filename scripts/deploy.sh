#!/usr/bin/env bash
set -euo pipefail

: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
: "${RUNTIME_SERVICE_ACCOUNT:?Set RUNTIME_SERVICE_ACCOUNT}"

REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-agentic-rag-assistant}"
FIRESTORE_COLLECTION="${FIRESTORE_COLLECTION:-rag_chunks}"

# Firestore is durable and uses Cloud Run's short-lived service identity.
# Secret Manager versions must exist for Gemini and API access keys.
# This service remains private (Cloud Run IAM + X-API-Key required).
gcloud run deploy "$SERVICE" \
  --project "$GOOGLE_CLOUD_PROJECT" \
  --region "$REGION" \
  --source . \
  --service-account "$RUNTIME_SERVICE_ACCOUNT" \
  --no-allow-unauthenticated \
  --set-env-vars "CHROMA_MODE=firestore,FIRESTORE_COLLECTION=$FIRESTORE_COLLECTION,GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_GENAI_USE_VERTEXAI=FALSE" \
  --set-secrets "GEMINI_API_KEY=gemini-api-key:latest,GOOGLE_API_KEY=gemini-api-key:latest,API_ACCESS_KEY=rag-api-access-key:latest" \
  --memory 1Gi \
  --concurrency 8 \
  --min-instances 0 \
  --max-instances 2 \
  --timeout 300
