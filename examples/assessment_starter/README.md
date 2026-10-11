# Assessment starter: LegoAI reference consumer

Architecture boundary: this older direct-Model example imports private Core
reference implementations, including its optional Ollama adapter. It is not a
current public governed-host consumption recipe. New applications should follow
[the assembly guide](../../docs/ASSEMBLING-APPLICATIONS.md) and public
`legoai.runtime.local` API. Migration is recorded as audit debt in
[the conformance audit](../../planning/LEGOAI-ARCHITECTURE-DESIGN-CONFORMANCE-AUDIT-1.md);
the example's existing behavior and qualification scope are unchanged.

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
uv run uvicorn assessment_starter.main:app --host 127.0.0.1 --port 8001
```

```powershell
cd frontend
npm ci
npm run dev
```

Open Vite's printed URL. The dev proxy sends /api to port 8001.
GET /health on port 8001 reports health; POST /api/v1/ask accepts
{"question":"Hello"}. The fixed answer is intentional. In default fixed mode, no external model, key,
network service or tokens are needed after dependencies are installed.
Use npm.cmd on Windows if PowerShell blocks npm.ps1.

The backend has its own environment and editable dependency on the repository
root. No frontend/backend runtime dependencies are added to the LegoAI package.
Settings and ModelPort are passed explicitly to create_app. The server entry point
reads validated model settings from environment variables once at startup.
Startup loads backend/.env, then applies shell-variable overrides without mutating the process environment.

## Verify

From backend:

```powershell
uv run pytest
uv run mypy src tests
uv run ruff check .
uv run ruff format --check .
```

From frontend: `npm test`, `npm run build` and `npm run lint`.
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
Additional providers need explicit credentials, timeout, cancellation and
error semantics. Built frontend assets need a same-origin /api reverse proxy;
Vite preview alone is not a full-stack deployment. Docker is unnecessary here.

Frontend tests use Vitest, React Testing Library and mocked fetch: no running backend or external network is needed. Use npm run test:watch for watch mode. Regenerate standalone projects to receive these tests.

## Choose the model

The application model factory is `backend/src/assessment_starter/model_factory.py`.
`fixtures.py` only constructs the offline test fixture. The API and service do not
construct providers. `main.py` reads validated environment settings once at startup
and calls this factory. Programmatic `create_app(settings, model=...)` supports
explicit injection, which takes precedence over the configured provider.

Default: `MODEL_PROVIDER=fixed`. No model call or API key is required.

For Ollama, in the backend terminal (replace the model name with one installed
on your Ollama server):

```powershell
$env:MODEL_PROVIDER = "ollama"
$env:OLLAMA_MODEL = "your-installed-chat-model"
$env:OLLAMA_BASE_URL = "http://127.0.0.1:11434"
$env:MODEL_TIMEOUT_SECONDS = "10"
uv run uvicorn assessment_starter.main:app --host 127.0.0.1 --port 8001
```

Restart the backend after changing settings. The frontend proxy must use the same
backend port (currently 8001). To return offline, set `$env:MODEL_PROVIDER = "fixed"`
and restart. .env.example lists available variables; backend/.env is loaded automatically at startup; shell variables override it. Invalid providers, missing Ollama model names or invalid URLs/timeouts
fail startup. There is no fallback to the fake when Ollama fails.

The in-repository example uses the existing LegoAI Ollama adapter. Its required
embedding-model field has an unused placeholder; this application never calls
embedding. Generated standalone projects use a Chat-only standard-library adapter
in `backend/src/app/ollama.py`, selected by `backend/src/app/model_factory.py`.
They contain no platform imports. The standalone response-read ceiling is 1 MiB;
this does not bound provider generation. The existing LegoAI adapter retains its
existing buffered transport behavior.

Both use the [Ollama Chat API](https://docs.ollama.com/api/chat) with streaming
disabled. Provider failures return a safe HTTP 502 without raw provider text.
No retry is attempted. The socket timeout is not an overall generation deadline;
cancelling the waiting coroutine does not stop its underlying blocking worker.
Authenticated/hosted providers and production authorization remain out of scope.

.env paths are resolved relative to the backend source package, not your terminal directory. Restart after edits. .env files stay excluded from exports and Git; only .env.example is shipped. Clear stale MODEL_PROVIDER shell overrides if the file seems ignored.
