# DocuMind CLI (`legoai-documind`)

LegoAI v0.1's first runnable governed AI application: ingest documents,
then ask questions over them and get a cited answer. Every embedding and
chat call is routed through LegoAI's governed runtime (Catalog ->
resolution -> authorization -> dispatch -> Coordinator) before ever
reaching Ollama -- this application never calls the Ollama Adapter
directly.

## Prerequisites

- Python 3.14, [uv](https://docs.astral.sh/uv/).
- [Ollama](https://ollama.com) running locally (default `http://localhost:11434`).

## Install and run

```
# from the repository root
uv sync

# pull the two required local models
ollama pull llama3.2
ollama pull nomic-embed-text

cd examples/documind
uv sync

uv run legoai-documind status
uv run legoai-documind ingest ./testdata
uv run legoai-documind ask "What retrieval approach does the Document Capability Pack use in v0.1?"
```

`ingest` accepts one or more files or directories (directories are walked
recursively); `ask` accepts one question in quotes. Re-running `ingest` on
the same file path replaces that document's previously-indexed chunks --
it never duplicates them.

Supported file extensions: `.txt`, `.md`/`.markdown`, `.html`/`.htm`, `.pdf`.

## Configuration

All configuration is via environment variables; every default is a
documented local-Ollama convention, never a hidden machine-specific value.

| Variable | Default | Meaning |
|---|---|---|
| `LEGOAI_DOCUMIND_OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama base URL |
| `LEGOAI_DOCUMIND_CHAT_MODEL` | `llama3.2` | chat/generation model |
| `LEGOAI_DOCUMIND_EMBEDDING_MODEL` | `nomic-embed-text` | embedding model |
| `LEGOAI_DOCUMIND_TIMEOUT_SECONDS` | `60` | HTTP timeout per Ollama request |
| `LEGOAI_DOCUMIND_INDEX_PATH` | `.legoai-documind/index.sqlite3` | local retrieval index file |
| `LEGOAI_DOCUMIND_TENANT_ID` | `local` | tenant scope for ingestion/retrieval |

No authentication/secret configuration exists: a local Ollama instance
requires none.

## Architecture note

```
DocuMind CLI (this package, documind_app)
  -> legoai_document.ingestion / .answering
       -> legoai_document.embedding / .retrieval / .rerank
  -> legoai.runtime._composition.model_governed (governed chat/embedding)
       -> legoai Catalog / resolution / authorization / dispatch / Coordinator
            -> legoai.reference.model.OllamaModelAdapter -> Ollama (HTTP)
```

`legoai_document` never constructs a `Catalog`, `ExecutionCoordinator`, or
`ModelPort` -- it receives `governed_embed`/`governed_chat` as plain async
callables from `documind_app.composition`, which is this application's own
composition root (see `src/documind_app/composition.py`). This mirrors
`legoai`'s own Internal-vs-Public Port/reference-realization split: an
application composes reference realizations behind Core's stable public
contracts, never the other way around.

Retrieval is a local SQLite-backed store combining brute-force cosine
vector similarity and deterministic lexical word-overlap scoring via
Reciprocal Rank Fusion (`k = 60`). Reranking is the identity/truncation
reference reranker -- a legitimate, explicitly-declared v0.1 choice, not a
silent fallback.

## Known limitations (v0.1)

- One Model provider only: local Ollama over HTTP. No multi-provider
  fallback -- an unreachable Ollama instance is reported as an error, never
  silently routed elsewhere.
- Local, single-process, single-operator trust model: one fixed local
  principal with a standing Grant for both published capabilities. No
  Approval workflow, no Policy supersession, no untrusted-Plugin isolation.
- Retrieval and the Catalog/Grant/Approval/Policy state are process-lifetime
  in memory (Catalog, Grants) or a local SQLite file (the retrieval index)
  -- nothing survives a process crash mid-invocation as a persisted
  operation ledger; no restart-recovery is implemented.
- No exactly-once guarantee for the effectful Model call across a network
  failure: a concurrent double-invocation of the *same* authorized
  execution is prevented, but a client-observed timeout does not guarantee
  the provider never completed the request (`EffectExtent.UNKNOWN`).
- Context budgeting is a plain character-count approximation, not a real
  tokenizer.
- No OCR / scanned-PDF support (inherited from `document.parsing`).
- No Cohere/any hosted reranker; identity/truncation only.

## Testing

The default test suite (`uv run python -m pytest`) fakes the Ollama HTTP
boundary and requires no running Ollama instance. A live smoke test against
a real local Ollama instance can be run manually:

```
uv run legoai-documind status
uv run legoai-documind ingest ./testdata
uv run legoai-documind ask "What retrieval approach does the Document Capability Pack use in v0.1?"
```
