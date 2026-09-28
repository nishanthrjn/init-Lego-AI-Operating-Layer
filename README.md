# LegoAI

The [browser-local hand-landmark slice](planning/BROWSER-HAND-LANDMARK-VERTICAL-SLICE.md)
is implemented with local validation pending. It is isolated from Python Core;
run its user validation launcher before the manual camera smoke test.

A narrow [configuration-selected Model composition proof](docs/model-composition.md)
now builds on admitted Catalog contributions and existing governed invocation.
It includes two adapter realizations with offline substitution tests; live-provider
behavioral qualification and a public application-authoring facade remain future work.

LegoAI is a Python-first platform and reusable component ecosystem for composing
governed AI applications. Reusable Python capabilities and the governed runtime
are its implementation foundation; providers, frameworks and protocols integrate
through optional adapters. See the [current intent amendment](intent-amendments/IA-001.md)
and [forward roadmap](planning/PYTHON-FIRST-REUSABLE-AI-PLATFORM-PLAN.md).
Production-grade operation across the target catalog is the destination;
[v0.1 qualification](planning/V0.1-RELEASE-READINESS.md) covers the documented
local DocuMind scope. The minimal one-step Agent foundation is locally qualified
for its documented scope; Workflows, Teams and ForgeAI remain planned.

M8.1 Repository Analyst is locally qualified for its documented scope.
It composes authorized bounded file reads with the existing one-step Agent and
governed Model routing. See the [contract and validation commands](packages/legoai-engineering/README.md#m81--repository-analyst).
M1–M7 retain their qualified scopes. M8.2 Independent Reviewer is locally qualified
for bounded supplied-text review. See the
[Reviewer contract and local commands](packages/legoai-engineering/README.md#m82--independent-reviewer).

M8.3 Bounded Coding Agent implementation is complete with local validation pending.
It proposes M4-compatible CREATE/UPDATE changesets after authorized bounded reads;
it never applies or executes them. See the
[Coding contract and validation script](packages/legoai-engineering/README.md#m83--bounded-coding-agent).
M8.4 remains unstarted.

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

The [`legoai-collation`](packages/legoai-collation/) pack is a pure,
dependency-free slice: source-linked field readings, text/decimal/choice
normalization, and single-field precedence collation that keeps every
disagreement visible. It has no Core dependency and `legoai` never imports it.
See its [README](packages/legoai-collation/README.md) for the contract and
local commands.

The new [`legoai-engineering`](packages/legoai-engineering/) pack is a separate
first foundation milestone: pure inspection of supplied repository text with an
intake example. M1 local validation is complete, as recorded in the forward plan.
M2 adds a bounded read-only local workspace adapter and an example reusing M1;
M2 local validation is complete for its documented trusted local scope.
M3 adds typed read-only Git observation and is locally validated. M4 adds bounded
text changesets with digest preconditions; implementation and local validation
are complete for the documented trusted local scope. M5 adds typed pytest,
Ruff check/format-check and mypy operations; implementation and local validation
are complete for the documented scope. These execute trusted local code without isolation.
Governed runtime publication, Git mutation and engineering Agents remain
unimplemented. M6 adds a separate bounded Python sandbox capability targeting
Docker Desktop Linux. Implementation and local qualification are complete for
the documented bounded workload scope; see the [M6 completion report](planning/ENGINEERING-M6-IMPLEMENTATION.md#completion-report).
Engineering workload isolation is distinct from Plugin isolation: ADR-012 remains
Proposed. [M6.5 model routing](docs/model-routing.md) is implemented and locally
validated. It maps logical Chat profiles to immutable configured model
bindings without provider I/O or authorization; actual calls retain governed
execution. [M7 Agent foundation](docs/agent.md) adds a single governed Chat step
with bounded accepted output; implementation and local qualification are complete.
M8 specialized engineering Agents remain unstarted.

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

See [foundational ports and adapters](docs/ports-and-adapters.md) for existing contracts, offline injection and persistence test support.


Local ComfyUI text-to-image integration is implemented in the optional
[generative-media package](packages/legoai-generative-media/README.md).
[Local validation is pending](planning/COMFYUI-TEXT-TO-IMAGE-VERTICAL-SLICE.md);
ComfyUI remains an external operator-managed runtime.
