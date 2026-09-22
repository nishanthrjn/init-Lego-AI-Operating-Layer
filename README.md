# LegoAI

LegoAI is a Python-first platform and reusable component ecosystem for composing
governed AI applications. Reusable Python capabilities and the governed runtime
are its implementation foundation; providers, frameworks and protocols integrate
through optional adapters. See the [current intent amendment](intent-amendments/IA-001.md)
and [forward roadmap](planning/PYTHON-FIRST-REUSABLE-AI-PLATFORM-PLAN.md).
Production-grade operation across the target catalog is the destination;
[v0.1 qualification](planning/V0.1-RELEASE-READINESS.md) covers the documented
local DocuMind scope. Agents, Workflows, Teams and ForgeAI remain planned.

Every governed capability
invocation -- including calls to an external Model provider -- passes through
a Catalog, capability resolution, current authorization, and a dispatch
arbiter before any provider is ever invoked. See [intent.md](intent.md) and
[SPEC.md](SPEC.md) for the canonical specification; this README is a
quickstart, not a restatement of that authority.

## Packages

- `legoai` (this repository's `src/legoai`) -- the governed Core runtime:
  Catalog, capability resolution, governance, execution/dispatch,
  the `legoai.intelligence.model` Model contract, and reference realizations
  (including the Ollama `ModelPort` Adapter).
- [`legoai-document`](packages/legoai-document/) -- the Document Capability
  Pack: `document.parsing`, `.chunking`, `.embedding`, `.retrieval`,
  `.rerank`, `.ingestion`, `.answering`. Depends only on `legoai`'s stable
  public contracts; `legoai` never imports it.
- [`legoai-documind`](examples/documind/) -- LegoAI v0.1's first runnable
  governed AI application: a CLI that ingests documents and answers
  questions over them, using `legoai-document`'s capabilities composed
  through `legoai`'s governed runtime and a local Ollama instance.

The new [`legoai-engineering`](packages/legoai-engineering/) pack is a separate
first foundation milestone: pure inspection of supplied repository text with an
intake example. M1 local validation is complete, as recorded in the forward plan.
M2 adds a bounded read-only local workspace adapter and an example reusing M1;
M2 local validation is pending. Governed runtime publication, Git, code execution
and engineering Agents remain unimplemented.

## Quickstart: the DocuMind CLI

```
uv sync
ollama pull llama3.2
ollama pull nomic-embed-text
cd examples/documind
uv sync
uv run legoai-documind status
uv run legoai-documind ingest ./testdata
uv run legoai-documind ask "What retrieval approach does the Document Capability Pack use in v0.1?"
```

See [examples/documind/README.md](examples/documind/README.md) for full
setup, configuration, and known limitations.

## Development

See [docs/development.md](docs/development.md) for running this
package's own test suite, mypy, and ruff.
