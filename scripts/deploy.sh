#!/usr/bin/env bash
set -euo pipefail

: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
: "${CHROMA_TENANT:?Set CHROMA_TENANT}"
: "${CHROMA_DATABASE:?Set CHROMA_DATABASE}"

REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-agentic-rag-assistant}"

# Uses private IAM ingress. Provision Secret Manager secrets and runtime service
# account access before invoking. Do not pass secrets as command-line values.
gcloud run deploy "$SERVICE"   --project "$GOOGLE_CLOUD_PROJECT"   --region "$REGION"   --source .   --no-allow-unauthenticated   --set-env-vars "CHROMA_MODE=cloud,CHROMA_TENANT=$CHROMA_TENANT,CHROMA_DATABASE=$CHROMA_DATABASE"   --set-secrets "GEMINI_API_KEY=gemini-api-key:latest,CHROMA_API_KEY=chroma-api-key:latest,API_ACCESS_KEY=rag-api-access-key:latest"   --memory 1Gi   --timeout 300
