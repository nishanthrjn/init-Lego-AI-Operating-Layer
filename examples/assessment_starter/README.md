# Assessment starter: LegoAI reference consumer

A maintained, offline example: React → FastAPI → AnswerService → existing
ModelPort → existing FixedModel. It validates direct application consumption,
without routing, governance, execution, Agents, persistence, embeddings or RAG.
The small model.py module only re-exports existing types; it defines no new
LegoAI contracts. Fixtures construct ChatResult using ModelId, ProviderId and
ModelUsage(0, 0). Zero usage is a fact of this offline fixture.

## Run locally

Python 3.14, uv and Node.js 22.12+ (or Node 24) are required.
From this directory, in separate terminals:

```powershell
cd backend
uv sync --locked
uv run uvicorn assessment_starter.main:app --host 127.0.0.1 --port 8000
```

```powershell
cd frontend
npm ci
npm run dev
```

Open Vite's printed URL. The dev proxy sends /api to port 8000.
GET /health on port 8000 reports health; POST /api/v1/ask accepts
{"question":"Hello"}. The fixed answer is intentional. No external model, key,
network service or tokens are needed after dependencies are installed.
Use npm.cmd on Windows if PowerShell blocks npm.ps1.

The backend has its own environment and editable dependency on the repository
root. No frontend/backend runtime dependencies are added to the LegoAI package.
Settings and ModelPort are passed explicitly to create_app. .env.example is
documentation; the app does not implicitly load environment variables or secrets.

## Verify

From backend:

```powershell
uv run pytest
uv run mypy src tests
uv run ruff check .
uv run ruff format --check .
```

From frontend: `npm run build` and `npm run lint`.
Backend tests use an in-process TestClient and forbid external socket connections.

## Export a standalone project

From the LegoAI repository root:

```powershell
python scripts/export_assessment_starter.py --destination "D:\Work\Assessments\recall-space-assessment"
```

The standard-library exporter copies an explicit file allowlist, rewrites the
application package to app, and generates a validated Chat-only ModelPort,
request/result values and FixedModel. No installed LegoAI package is needed to
run the exporter. Generated code has no platform imports or relative dependency
on this repository. Backend dependencies resolve independently on first uv sync;
the frontend package lock is carried over.

Existing destinations are rejected unless --force is explicit. Force replaces
only generated files, preserves unrelated files and does not merge local edits.
Source repository paths, symlinks/junctions, and hardlinked outputs are rejected.
A trusted local filesystem is assumed; concurrent hostile filesystem mutation
and whole-export transactionality are not guaranteed. Individual file replacement
is atomic. No Git initialization or commits are performed.

The exporter never copies caches, environments, secrets, data, Git metadata,
unrelated documentation or examples. Tests, package manifests and frontend source
are maintained here, then regenerated. Reduced standalone model/fixture text is
maintained in scripts/export_assessment_starter.py, not a second application tree.

This is an offline local starter, not an authenticated production deployment.
A future provider adapter needs explicit credentials, timeout, cancellation and
error semantics. Built frontend assets need a same-origin /api reverse proxy;
Vite preview alone is not a full-stack deployment. Docker is unnecessary here.
