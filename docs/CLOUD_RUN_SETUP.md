# Deploy Agentic RAG on Google Cloud Run with Firestore vector search

**Why Firestore?** Chroma Cloud stopped accepting new signups following its October 2026 wind-down announcement. This project now uses **ChromaDB PersistentClient locally** and **Firestore vector search on Cloud Run**. You need no Chroma Cloud account. This changes the hosted vector store, but keeps Gemini, Google ADK, FastAPI, and Cloud Run.

## Prerequisites

- A Google Cloud project with billing enabled
- Gemini Developer API key from https://aistudio.google.com/app/apikey
- Permissions to manage IAM, Secret Manager, Firestore, and Cloud Run
- Google Cloud CLI installed and authenticated locally
- A GitHub repository already containing the project

**Never provide your Gemini/API access keys to this chat or commit them to GitHub.**

## 1. Prepare Google Cloud resources

~~~bash
export PROJECT_ID="YOUR_PROJECT_ID"
gcloud auth login
gcloud config set project "$PROJECT_ID"

gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com \
  firestore.googleapis.com iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com

export PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
~~~

Create a **Firestore database in Native mode**, choosing an appropriate region. Use the [Firestore console](https://console.cloud.google.com/firestore/databases). An existing default Firestore database is also fine.

Then create the vector index. **The vector dimension must equal the GEMINI embedding output dimensionality** configured by this app (default 768):

~~~bash
gcloud firestore indexes composite create \
  --collection-group="rag_chunks" \
  --query-scope=COLLECTION \
  --field-config field-path=embedding,vector-config='{"dimension":"768","flat":"{}"}' \
  --database="(default)"
~~~

Wait until the index finishes building (check Firestore > Indexes). **Firestore vector search fails until the index is ready.** If an index already exists, do not create a duplicate.

## 2. Create secrets in Secret Manager

Create two secrets, each with an actual value/version:

| Secret ID | Store this confidential value |
| --- | --- |
| `gemini-api-key` | Gemini Developer API key |
| `rag-api-access-key` | A long, cryptographically random string; your separate application API key |

Use the [Google Secret Manager console](https://console.cloud.google.com/security/secret-manager) to create them. Do not add keys to repository variables or logs.

## 3. Create identities and grant permissions

~~~bash
gcloud iam service-accounts create rag-github-deployer \
  --display-name="RAG GitHub deployer"
gcloud iam service-accounts create rag-cloudrun-runtime \
  --display-name="RAG runtime"

export DEPLOY_SA="rag-github-deployer@$PROJECT_ID.iam.gserviceaccount.com"
export RUNTIME_SA="rag-cloudrun-runtime@$PROJECT_ID.iam.gserviceaccount.com"

# For a demo: project-wide permissions for deployment. Restrict these in production.
for ROLE in roles/run.admin roles/cloudbuild.builds.editor roles/artifactregistry.admin roles/storage.admin; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$DEPLOY_SA" --role="$ROLE"
done

gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_SA" \
  --member="serviceAccount:$DEPLOY_SA" \
  --role="roles/iam.serviceAccountUser"

# Firestore access only from the runtime identity.
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$RUNTIME_SA" \
  --role="roles/datastore.user"

for SECRET in gemini-api-key rag-api-access-key; do
  gcloud secrets add-iam-policy-binding "$SECRET" \
    --member="serviceAccount:$RUNTIME_SA" \
    --role="roles/secretmanager.secretAccessor"
done
~~~

Cloud Build's build service account may also need role assignments depending on your Google Cloud project's configuration.

## 4. Enable GitHub Workload Identity Federation (no JSON key)

~~~bash
gcloud iam workload-identity-pools create github-rag \
  --location="global" --display-name="RAG GitHub Actions"

gcloud iam workload-identity-pools providers create-oidc github-main \
  --location="global" --workload-identity-pool="github-rag" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository=='BhushanVidhate-27/agentic-rag-google-cloud' && assertion.ref=='refs/heads/main'"

gcloud iam service-accounts add-iam-policy-binding "$DEPLOY_SA" \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github-rag/attribute.repository/BhushanVidhate-27/agentic-rag-google-cloud" \
  --role="roles/iam.workloadIdentityUser"
~~~

If the pool/provider already exists, inspect and reuse rather than overwrite it. Federation reference: https://github.com/google-github-actions/auth

## 5. Add nonsecret GitHub Actions variables

Open https://github.com/BhushanVidhate-27/agentic-rag-google-cloud/settings/variables/actions

| Variable | Example/meaning |
| --- | --- |
| `GCP_PROJECT_ID` | Your actual GCP project ID |
| `GCP_WIF_PROVIDER` | `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-rag/providers/github-main` |
| `GCP_DEPLOY_SA` | `rag-github-deployer@PROJECT_ID.iam.gserviceaccount.com` |
| `GCP_RUNTIME_SA` | `rag-cloudrun-runtime@PROJECT_ID.iam.gserviceaccount.com` |
| `GCP_REGION` | `us-central1` or your preferred Cloud Run region |
| `FIRESTORE_COLLECTION` | `rag_chunks` (optional; must match vector index collection group) |

Ensure the GitHub **production** environment exists and allows deployment from main.

## 6. Deploy manually

Go to https://github.com/BhushanVidhate-27/agentic-rag-google-cloud/actions/workflows/deploy-cloud-run.yml and click **Run workflow** on main.

The workflow deploys a private Cloud Run service, injects secrets by reference, and configures `CHROMA_MODE=firestore`. Your GitHub repository does not need any external vector-database signup.

## 7. Smoke test and evaluate against real Gemini

An identity granted `roles/run.invoker` on the service can call the private Cloud Run URL. Set the API key in your local shell without printing or committing it.

~~~bash
export REGION="us-central1"
export URL="$(gcloud run services describe agentic-rag-assistant \
  --region "$REGION" --format='value(status.url)')"
export CLOUD_RUN_ID_TOKEN="$(gcloud auth print-identity-token)"

curl -fsS "$URL/health" -H "Authorization: Bearer $CLOUD_RUN_ID_TOKEN"

curl -fsS -X POST "$URL/v1/documents" \
  -H "Authorization: Bearer $CLOUD_RUN_ID_TOKEN" \
  -H "X-API-Key: $API_ACCESS_KEY" \
  -F "file=@examples/handbook.txt"

API_ACCESS_KEY="$API_ACCESS_KEY" CLOUD_RUN_ID_TOKEN="$CLOUD_RUN_ID_TOKEN" \
  python scripts/evaluate.py --dataset eval/sample.jsonl --base-url "$URL"
~~~

Do not report a benchmark score until you have run this against the actual deployed model and evaluation dataset. The evaluation script's substring metric is an approximation, not human-rated answer accuracy.

## Security, data, and cost

This starter is **single-tenant** and uses one shared API key. Retrieved documents may be confidential; do not expose the service publicly or use real private data without additional access controls. Firestore stores text snippets and vectors (not original PDF files). Cloud Run and Firestore have their own usage-based charges and quotas. Consider configuring Google Cloud budgets and alerts before deployment.

This route does **not** depend on Chroma Cloud. Local usage still runs on open-source ChromaDB.
