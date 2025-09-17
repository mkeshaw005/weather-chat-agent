# Deploying Azure Chat Demo API to Azure Container Apps

This document describes how to build and deploy the FastAPI-based service to Azure Container Apps.

The container exposes:
- `GET /healthz` for health checks
- `POST /chat` with body `{ "question": "..." }` returning `{ "answer": "..." }`

## Conversation persistence
This app now persists conversation history to SQLite by default and threads recent history into replies.

- Env vars:
  - `CHAT_DB_PATH` (default `./data/chat.db`)
  - `MAX_HISTORY_TURNS` (default `10`)

- `/chat` now accepts an optional `session_id` and always returns `session_id`:

```bash
# Start a new session (no session_id provided)
curl -s -X POST "http://127.0.0.1:8080/chat" -H "Content-Type: application/json" \
  -d '{"question":"Hello!"}'

# Continue the same session by passing the returned session_id
curl -s -X POST "http://127.0.0.1:8080/chat" -H "Content-Type: application/json" \
  -d '{"question":"What about Denver in June?","session_id":"<SESSION_ID_FROM_PREV_RESPONSE>"}'
```

- Session management endpoints:

```bash
# List sessions (most recent first)
curl -s "http://127.0.0.1:8080/sessions?limit=20"

# Get messages for a session
curl -s "http://127.0.0.1:8080/sessions/<SESSION_ID>/messages?limit=50"

# Delete a session (idempotent)
curl -s -X DELETE "http://127.0.0.1:8080/sessions/<SESSION_ID>"
```

## Prerequisites
- Azure CLI installed and logged in (`az login`).
- An Azure subscription where you can create resources.
- Docker installed locally (if you choose local build/push). Alternatively, use ACR Build.

## Environment variables required by the app
Set these values from your Azure OpenAI resource (not the Studio):

- `AZURE_OPENAI_ENDPOINT` like `https://<your-resource>.openai.azure.com/`
- `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME` matching your model deployment name
- `AZURE_OPENAI_API_KEY` from the Keys blade

Optional:
- `AZURE_OPENAI_API_VERSION` (e.g., `2024-10-21`)

## Azure CLI deployment steps
Replace placeholders (like `<...>`) with your values.

```bash
# 1) Login and select subscription
az login
az account set --subscription "<SUBSCRIPTION_ID>"

# 2) Variables
LOCATION="westus3"
RG="rg-azure-chat-demo"
ACR="acrchatdemo$RANDOM"
LOG="law-azure-chat-demo"
ENV="cae-azure-chat-demo"
APP="aca-azure-chat-demo"

# Azure OpenAI config
AZURE_OPENAI_ENDPOINT="https://azure-open-ai-mshaw-2025.openai.azure.com/"
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME="gpt-4-1-nano-2025-04-14"
AZURE_OPENAI_API_KEY="<your-azure-openai-api-key>"

# 3) Create resource group and ACR
az group create -n "$RG" -l "$LOCATION"
az acr create -n "$ACR" -g "$RG" --sku Basic --admin-enabled true
ACR_LOGIN_SERVER=$(az acr show -n "$ACR" -g "$RG" --query loginServer -o tsv)

# 4) Build and push the container image

## Apple Silicon (ARM64) users
Azure Container Apps requires linux/amd64 images. If you are on an Apple Silicon Mac (ARM64), either build with Docker Buildx targeting amd64 or use ACR Build (which builds on Azure for amd64).

Option A (Buildx on your Mac, one-time setup then build and push):

```bash
# One-time: enable buildx
docker buildx create --use

# Prefer a unique tag to avoid cache confusion
TAG="v$(date +%Y%m%d-%H%M%S)"
IMAGE="$ACR_LOGIN_SERVER/azure-chat-demo:$TAG"

az acr login -n "$ACR"
docker buildx build --platform linux/amd64 -t "$IMAGE" --push .

# Use this image in the az containerapp create/update step
```

Option B (ACR Build on Azure for amd64):

```bash
TAG="v$(date +%Y%m%d-%H%M%S)"
IMAGE="azure-chat-demo:$TAG"
az acr build -r "$ACR" -g "$RG" -t "$IMAGE" .
IMAGE="$ACR_LOGIN_SERVER/$IMAGE"

# Use this image in the az containerapp create/update step
```

# Option A: Local Docker
IMAGE="$ACR_LOGIN_SERVER/azure-chat-demo:latest"
az acr login -n "$ACR"
docker build -t "$IMAGE" .
docker push "$IMAGE"

# Option B: ACR Build (no local Docker engine required)
# IMAGE="azure-chat-demo:latest"
# az acr build -r "$ACR" -g "$RG" -t "$IMAGE" .
# IMAGE="$ACR_LOGIN_SERVER/$IMAGE"

# 5) Create Log Analytics and Container Apps Environment
az monitor log-analytics workspace create -g "$RG" -n "$LOG" -l "$LOCATION"
LOG_ID=$(az monitor log-analytics workspace show -g "$RG" -n "$LOG" --query customerId -o tsv)
LOG_KEY=$(az monitor log-analytics workspace get-shared-keys -g "$RG" -n "$LOG" --query primarySharedKey -o tsv)

az containerapp env create \
  -g "$RG" \
  -n "$ENV" \
  -l "$LOCATION" \
  --logs-destination log-analytics \
  --logs-workspace-id "$LOG_ID" \
  --logs-workspace-key "$LOG_KEY"

# 6) Create the Container App with ingress and secrets
az containerapp create \
  -g "$RG" \
  -n "$APP" \
  --environment "$ENV" \
  --image "$IMAGE" \
  --ingress external \
  --target-port 8080 \
  --registry-server "$ACR_LOGIN_SERVER" \
  --registry-identity system \
  --min-replicas 0 \
  --max-replicas 3 \
  --cpu "0.5" --memory "1.0Gi" \
  --secrets "azure-openai-api-key=$AZURE_OPENAI_API_KEY" \
  --env-vars \
      "AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT" \
      "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=$AZURE_OPENAI_CHAT_DEPLOYMENT_NAME" \
      "AZURE_OPENAI_API_KEY=secretref:azure-openai-api-key"

# 7) Get the URL and test
FQDN=$(az containerapp show -g "$RG" -n "$APP" --query properties.configuration.ingress.fqdn -o tsv)
echo "https://$FQDN"

# Test health endpoint
curl -i "https://$FQDN/healthz"

# Test chat endpoint
curl -s -X POST "https://$FQDN/chat" -H "Content-Type: application/json" \
  -d '{"question":"What is the average temperature in Seattle in June?"}'
```

## Updating ACR and ACA after local changes
When you change code, build a new image tag, push to ACR, then update the Container App to roll out the new image.

Option A (Docker Buildx; ensures linux/amd64 on Apple Silicon):

```bash
TAG="v$(date +%Y%m%d-%H%M%S)"
IMAGE="$ACR_LOGIN_SERVER/azure-chat-demo:$TAG"

az acr login -n "$ACR"
docker buildx create --use 2>/dev/null || true
docker buildx build --platform linux/amd64 -t "$IMAGE" --push .

# Update ACA to the new image (creates a new revision and rolls traffic)
az containerapp update -g "$RG" -n "$APP" --image "$IMAGE"

# (Optional) Watch rollout
az containerapp revision list -g "$RG" -n "$APP" -o table
```

Option B (ACR Build on Azure):

```bash
TAG="v$(date +%Y%m%d-%H%M%S)"
IMAGE="azure-chat-demo:$TAG"
az acr build -g "$RG" -r "$ACR" -t "$IMAGE" .
IMAGE="$ACR_LOGIN_SERVER/$IMAGE"

az containerapp update -g "$RG" -n "$APP" --image "$IMAGE"
```

Notes:
- Use unique tags to avoid “latest” caching issues.
- If your app has min-replicas 0, the first request after update may take a few seconds due to cold start.
- Rollback: list revisions and set an earlier one active if needed:

```bash
az containerapp revision list -g "$RG" -n "$APP" -o table
az containerapp revision set-mode -g "$RG" -n "$APP" --mode single
az containerapp revision activate -g "$RG" -n "$APP" --revision "<REVISION_NAME>"
```

## Running locally (optional)
You can run the API locally with Uvicorn after setting your `.env`.

```bash
# Install deps
python -m venv .venv
./.venv/bin/pip install -r requirements.txt

# Create and populate .env with your Azure OpenAI values
cp .env.example .env
# edit .env with your values

# Run the server
./.venv/bin/uvicorn app.api:app --host 0.0.0.0 --port 8080 --reload

# Test locally
curl -s -X POST "http://127.0.0.1:8080/chat" -H "Content-Type: application/json" \
  -d '{"question":"What is the average temperature in Seattle in June?"}'
```

Trouble shooting:
az containerapp revision list -g "$RG" -n "$APP" -o table
az containerapp revision show -g "$RG" -n "$APP" --revision "aca-azure-chat-demo--0000002" -o jsonc
az containerapp logs show -g "$RG" -n "$APP" --type app --follow
az containerapp logs show -g "$RG" -n "$APP" --type system --follow