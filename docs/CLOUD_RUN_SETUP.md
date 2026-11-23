# Cloud Run launch checklist

This repo contains a **manual GitHub Actions deployment workflow**. It does not have permission to create Google Cloud accounts, obtain your Gemini key, or provision a billing-enabled project by itself.

## 1. Prepare external services (user action)

1. Create/select a billing-enabled Google Cloud project: https://console.cloud.google.com/
2. Obtain a **Gemini Developer API** key in Google AI Studio: https://aistudio.google.com/app/apikey
3. Create a Chroma Cloud database and API key at https://www.trychroma.com/. Local Chroma storage is **not durable on Cloud Run**.
4. Use Google Cloud Secret Manager https://console.cloud.google.com/security/secret-manager to create **three secrets with actual versions**:
   - gemini-api-key: your Gemini Developer API key
   - chroma-api-key: your Chroma Cloud API key
   - rag-api-access-key: a long, random string used in the X-API-Key header
5. Never put these secret values in GitHub repository variables, source code, issues, comments, logs, or chat messages.

## 2. Enable APIs and provision two service accounts

Install the Google Cloud CLI, authenticate using your Google account, and select the project:

~~~bash
export PROJECT_ID="YOUR_PROJECT_ID"
gcloud auth login
gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com \
  iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com

export PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
gcloud iam service-accounts create rag-github-deployer --display-name="RAG GitHub deployer"
gcloud iam service-accounts create rag-cloudrun-runtime --display-name="RAG runtime"
export DEPLOY_SA="rag-github-deployer@$PROJECT_ID.iam.gserviceaccount.com"
export RUNTIME_SA="rag-cloudrun-runtime@$PROJECT_ID.iam.gserviceaccount.com"
~~~

Give your **deployer** only the rights needed to deploy source to Cloud Run, work with builds/artifacts, and act as the runtime service account. The sample below uses several project-wide roles for initial setup; tighten these by resource/role in production.

~~~bash
for ROLE in roles/run.admin roles/cloudbuild.builds.editor roles/artifactregistry.admin roles/storage.admin; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$DEPLOY_SA" --role="$ROLE"
done

gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_SA" \
  --member="serviceAccount:$DEPLOY_SA" --role="roles/iam.serviceAccountUser"
~~~

Cloud Build's build identity may need project-specific Cloud Build/Artifact Registry permissions depending on your existing project settings.

Allow the **runtime account**, not your repository, to access only the three required Secret Manager secrets:

~~~bash
for SECRET in gemini-api-key chroma-api-key rag-api-access-key; do
  gcloud secrets add-iam-policy-binding "$SECRET" \
    --member="serviceAccount:$RUNTIME_SA" \
    --role="roles/secretmanager.secretAccessor"
done
~~~

## 3. One-time GitHub OIDC federation

These commands restrict the trust provider to **this repository's main branch**. The GitHub workflow uses temporary OIDC credentials; no Google Cloud private service-account JSON key needs to be stored in GitHub.

~~~bash
gcloud iam workload-identity-pools create github-rag \
  --location="global" --display-name="RAG GitHub Actions"

gcloud iam workload-identity-pools providers create-oidc github-main \
  --location="global" \
  --workload-identity-pool="github-rag" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository=='BhushanVidhate-27/agentic-rag-google-cloud' && assertion.ref=='refs/heads/main'"

gcloud iam service-accounts add-iam-policy-binding "$DEPLOY_SA" \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github-rag/attribute.repository/BhushanVidhate-27/agentic-rag-google-cloud" \
  --role="roles/iam.workloadIdentityUser"
~~~

If a pool/provider already exists, inspect it and avoid overwriting its conditions. Documentation: https://github.com/google-github-actions/auth#setting-up-workload-identity-federation

## 4. Configure GitHub repository variables

Open https://github.com/BhushanVidhate-27/agentic-rag-google-cloud/settings/variables/actions

Under **Repository variables**, add the following **non-secret** values:

| Name | Value |
| ---- | ----- |
| GCP_PROJECT_ID | your Google Cloud project ID |
| GCP_WIF_PROVIDER | projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-rag/providers/github-main |
| GCP_DEPLOY_SA | rag-github-deployer@PROJECT_ID.iam.gserviceaccount.com |
| GCP_RUNTIME_SA | rag-cloudrun-runtime@PROJECT_ID.iam.gserviceaccount.com |
| GCP_REGION | us-central1 (or your chosen region) |
| CHROMA_TENANT | your Chroma Cloud tenant |
| CHROMA_DATABASE | your Chroma Cloud database |

Ensure the **production** GitHub environment exists and permits deployments from main. If environment-scoped variables are used instead, they must be available to the production job.

## 5. Start deployment

Open https://github.com/BhushanVidhate-27/agentic-rag-google-cloud/actions/workflows/deploy-cloud-run.yml

Choose **Run workflow**, select branch **main**, and run. Cloud Run service is **private**, and Secret Manager keys are injected by name. The job prints the new URL when deployment succeeds.

## 6. Run real smoke test and document evaluation

An authenticated Cloud Run caller must have roles/run.invoker for the service. For an interactive development account with that permission:

~~~bash
export REGION="us-central1"
export URL="$(gcloud run services describe agentic-rag-assistant --region "$REGION" --format='value(status.url)')"
export CLOUD_RUN_ID_TOKEN="$(gcloud auth print-identity-token)"
# In this terminal, securely provide the rag-api-access-key value as API_ACCESS_KEY.
# Do not paste it into the repository or a chat message.
curl -fsS "$URL/health" -H "Authorization: Bearer $CLOUD_RUN_ID_TOKEN"

curl -fsS -X POST "$URL/v1/documents" \
  -H "Authorization: Bearer $CLOUD_RUN_ID_TOKEN" \
  -H "X-API-Key: $API_ACCESS_KEY" \
  -F "file=@examples/handbook.txt"

python scripts/evaluate.py --dataset eval/sample.jsonl --base-url "$URL"
~~~

The evaluation script uses API_ACCESS_KEY and optionally CLOUD_RUN_ID_TOKEN from environment. Short-lived ID tokens expire and may need refreshing. **Report actual results only** after the API is configured and the evaluation runs.

## Costs, privacy, and caveats

Gemini embedding/generation, Chroma Cloud, Cloud Build, Artifact Registry, and Cloud Run can incur charges. The sample config caps Cloud Run at 2 instances and scales to zero when idle, but this does not cap total spend. This demonstration has **single-corpus API-key security**, so do not use it for sensitive multi-tenant datasets. Approval/billing/IAM setup must be completed by a Google Cloud project administrator.
