# Azure Chat Demo
Examples to use Azure with LLMs for Chat and learn how to use Azure OpenAI Service to create powerful AI-powered chat applications.

## Install the prerequisites

Use the `requirements.txt` to install all dependencies

```bash
python -m venv .venv
```

With pip:

```bash
./.venv/bin/pip install -r requirements.txt
```

With uv (requires allowing pre-releases due to `azure-ai-agents`):

```bash
uv pip install --prerelease=allow -r requirements.txt
```

Note: This project now targets Python 3.10 or newer due to updates in Semantic Kernel 1.x.

### Add your keys

Find the Azure OpenAI keys in the Azure OpenAI resource (not in the Studio). Add them to a local `.env` file at the project root. This repository ignores the `.env` file to prevent leaking secrets.

Your `.env` file should include at least the following for Azure OpenAI:

```
# Azure OpenAI (required for chat.py)
AZURE_OPENAI_ENDPOINT="https://<your-resource>.openai.azure.com/"
AZURE_OPENAI_API_KEY="<your-azure-openai-api-key>"
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME="<your-chat-deployment-name>"
```

If you plan to run Retrieval Augmented Generation (RAG) samples under `examples/`, you may also need Azure AI Search configuration. For those samples, you can add variables similar to the following (names may vary per example):

```
# Azure AI Search (optional, for RAG examples)
AZURE_SEARCH_ENDPOINT="https://<your-search-service>.search.windows.net"
AZURE_SEARCH_API_KEY="<your-search-admin-key>"
AZURE_SEARCH_INDEX_NAME="<your-index-name>"
```

### Run the demo

```bash
./.venv/bin/python chat.py
```

The top-level `chat.py` uses the latest Semantic Kernel (1.x) agent pattern with a simple tool. Ensure your Azure OpenAI deployment name, endpoint, and key are set in the `.env` file.

### Run the FastAPI API server

This repository includes a FastAPI-based HTTP API under `app/api.py` with Pydantic models in `app/models.py`.

Run the development server with uvicorn:

```bash
./.venv/bin/uvicorn app.api:app --reload
```

Once running, you can check:

- Health check: `GET http://127.0.0.1:8000/healthz`
- OpenAPI docs (Swagger UI): `http://127.0.0.1:8000/docs`

The primary routes include:

- `POST /chat` — Ask a question. Request/response schema: `ChatRequest`, `ChatResponse` from `app/models.py`.
- `GET /sessions` — List sessions. Response schema: `SessionSummaryDTO` from `app/models.py`.
- `GET /sessions/{session_id}/messages` — Get messages for a session. Response schema: `MessageDTO` from `app/models.py`.
- `DELETE /sessions/{session_id}` — Delete a session.

Example `curl` for chat:

```bash
curl -sS -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"Hello!","session_id":null}' | jq .
```

Note: The Pydantic DTOs have been moved out of `app/api.py` into `app/models.py` to keep route handlers focused and improve maintainability.

### Sample `.env`

You can copy `.env.example` to `.env` and update values:

```bash
cp .env.example .env
```

## Troubleshooting

- **uv cannot resolve dependencies (pre-release required)**
  - Error example: `No solution found ... azure-ai-agents<1.2.0b3 is available ... semantic-kernel==1.36.2 depends on azure-ai-agents>=1.2.0b3`.
  - Solution: install with uv using the pre-release flag: `uv pip install --prerelease=allow -r requirements.txt`.
  - Alternatively, use `pip install -r requirements.txt` which will install the explicitly requested pre-release version.

- **Environment variables not loading**
  - Confirm a `.env` file exists at the project root (`azure-chat-demo/`).
  - Ensure keys are spelled exactly as in this README (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME`).
  - The script calls `load_dotenv()`; if using a different shell, ensure you run from the project root.

- **Runtime error: missing environment variables**
  - The script raises an error if any required variables are missing. Double-check your `.env` and restart the process after editing.

- **401 Unauthorized or 403 Forbidden**
  - Verify `AZURE_OPENAI_API_KEY` comes from the Azure OpenAI resource (Keys blade), not the Studio.
  - Ensure your client IP/network is allowed by the resource’s network settings.
  - Confirm your Azure role/permissions allow access to the resource.

- **404 Not Found or Invalid deployment name**
  - `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME` must match an existing model deployment in your Azure OpenAI resource.
  - Be mindful of case and whitespace.

- **Endpoint format issues**
  - `AZURE_OPENAI_ENDPOINT` should be like `https://<resource-name>.openai.azure.com/` (with protocol and trailing domain).
  - Avoid trailing paths; only the base resource URL is needed.

- **API version problems**
  - By default, the SDK selects a compatible API version. If needed, set `AZURE_OPENAI_API_VERSION` to a supported version (e.g., `2024-10-21`).
  - Ensure your deployment model is compatible with the chosen API version.

- **Python version / dependency conflicts**
  - This project targets Python 3.10+. Verify with `python --version`.
  - Recreate your virtual environment and reinstall: `python -m venv .venv && ./.venv/bin/pip install -r requirements.txt`.

- **Network / Proxy issues**
  - If behind a corporate proxy, configure `HTTPS_PROXY`/`HTTP_PROXY` environment variables or your system proxy settings.

- **Semantic Kernel import or API changes**
  - Ensure you have the versions pinned in `requirements.txt` installed.
  - The project uses SK 1.x agent APIs (`ChatCompletionAgent`, `@kernel_function`). If you have older samples, APIs may differ.

- **Still stuck?**
  - Run a quick compilation check: `python -m compileall chat.py`.
  - Print your env values (without secrets) to verify they are loaded: add `print(os.getenv("AZURE_OPENAI_ENDPOINT"))` temporarily to `chat.py`.
  - Open an issue with your exact error message and environment details.