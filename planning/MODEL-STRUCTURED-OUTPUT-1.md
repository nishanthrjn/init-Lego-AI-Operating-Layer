# MODEL-STRUCTURED-OUTPUT-1

Status: **LOCALLY QUALIFIED (2026-10-08; offline; 63/63 validator phases);
live provider probe required separately.** This is a reusable LegoAI Core capability, and it
is offline only. No model or provider call was made. Unchanged:
- the EvidenceSufficiencyAgent, Analyst prompt and serialization;
- H1 and SAFETY-EVAL-2/3;
- the live harnesses.

Decision record: [ADR-022](../adrs/ADR-022.md) (Proposed).

## 1. What changed (Core)

| Area | Change |
| --- | --- |
| `legoai.intelligence.model.values` | New `JsonString`, `JsonArray`, `JsonObject`, `JsonSchema` (type alias), `StructuredOutputLimits`, `StructuredResponseFormat`; `ChatRequest.response_format: StructuredResponseFormat \| None = None` |
| `legoai.intelligence.model.routing` | `ModelBinding.structured_output: bool = False` (a capability fact) |
| `legoai.runtime.api` | `TrustedModelContribution.structured_output: bool = False` (explicit operator declaration) |
| `legoai.runtime.local` | Ollama bindings declare the capability; OpenAI-compatible bindings do not; trusted contributions follow their declaration |
| `legoai.runtime._composition.model_governed` | Routed chat refuses a structured request on an incapable binding before any call: FAILED, effect NONE, `VALIDATION_ERROR` (terminal) |
| `legoai.reference.model` (Ollama) | Sends the canonical schema as `format` only when a requirement is present |
| `legoai.reference.model_openai_compatible`, `legoai.reference.model_fake` | Refuse a structured request with `ModelPreflightError`; ordinary chat is unchanged |

The schema types live in `values.py`, because Core's boundary rules allow
`intelligence.model.values` to import only Kernel. Bounds are constants on
`StructuredOutputLimits`, because Core modules have no module-level state.

## 2. Schema subset and bounds

The subset comes from the current structured Agent results (the sufficiency
assessment shape):
- **object:** closed properties, emitted as `additionalProperties: false`,
  plus `required`;
- **string:** `enum`, `maxLength`, nullable (JSON type `["string","null"]`,
  with `null` added to a nullable enum);
- **array:** `items` and `maxItems`.

There are no `$ref`, `$defs`, remote references, recursion, numbers,
booleans, patterns or annotations.

| Bound | Value |
| --- | --- |
| Depth (root object = 1) | 6 |
| Properties per object | 32 |
| Schema nodes | 128 |
| Enum values / characters each | 32 / 128 |
| `maxLength` | 1–65,536 |
| `maxItems` | 1–256 |
| Canonical serialized size | 16 KiB |

Property names are lower-case identifiers. Required names must be unique and
declared. Duplicate enum values or properties are rejected. Serialization is
canonical (`json_schema()` returns a fresh object), and `digest()` is the
SHA-256 of the sorted-key compact encoding. Adapters cannot mutate caller
state.

## 3. Routing and fail-closed semantics

- **Ordinary chat:** unchanged.
- **Router:** unchanged. Exact profile matching; a single candidate resolves;
  several candidates are AMBIGUOUS. Capability never selects a candidate, and
  there is no fallback (tested).
- **Structured request on an incapable resolved binding:** refused before
  dispatch. It is never dropped, downgraded, retried or rerouted, and an
  explicit binding is never substituted.
- **Adapter backstops:** the OpenAI-compatible adapter and `FixedModel`
  refuse instead of ignoring.
- **Authority:** capability is not authority. Authorization is identical with
  or without `response_format` (tested).

**Error taxonomy:**
- invalid schema → construction-time `TypeError`/`ValueError`;
- capability refusal → `VALIDATION_ERROR`, NONE, terminal;
- adapter without support → `ModelPreflightError` (NONE);
- provider runtime failures → the existing Model error mapping.

## 4. Decisions

- **FixedModel and replay: B, remain incapable.** A fixed reply cannot honor
  a schema, so declaring support would be false. Trusted contributions
  default to incapable and must declare support explicitly.
- **OpenAI-compatible: deferred.** The provider-neutral contract maps
  naturally onto OpenAI-style JSON-schema response formats. Adapter support
  needs its own mapping, error semantics and qualification, so for now the
  adapter refuses.
- **No Core parsing.** Replies stay text. Consumers parse and validate.
- **Versioning.** An additive, backward-compatible Core contract change. The
  chat capability-offer version is unchanged.
- **Observability.** Safe metadata is available without a new platform:
  whether a requirement is present, the schema `digest()` and the binding's
  `structured_output`. No prompts, raw output or credentials are recorded.

## 5. Live provider status

The Ollama mapping uses the chat `format` field with a JSON-Schema object.
It is verified offline only, against a fake transport. Whether the qualified
Ollama 0.40.0 runtime honors every construct is **not established**:
- enums;
- `maxLength`/`maxItems`;
- nullable type arrays;
- `additionalProperties: false`.

**A separately authorized, minimal, non-semantic structured-output probe is
required** before any Agent relies on it. No probe was run.

## 6. Verification (offline)

New tests (57):
- `tests/unit/intelligence/test_structured_output.py` (24);
- `tests/unit/reference/test_model_structured_output.py` (11);
- `tests/integration/composition/test_structured_output_routing.py` (14);
- `tests/architecture/test_structured_output.py` (8).

One existing Core shape test (`test_model_routing.py`) gains the one additive
`ModelBinding` field.

**Pre-existing, unrelated failures:** Core
`test_package_install::test_build_and_fresh_wheel` and Engineering
`test_package_install::test_build_inventory_and_fresh_install` fail before
this slice, because their frozen inventories predate earlier modules. They
are deselected by exact id, with that reason, and not edited.

**Superseded assertions, deselected by id:**
- H1 `test_no_core_change`;
- SAFETY-LIVE-1 `test_no_agent_prompt_parser_changes`.

Both used "no `src` change since a base" as a proxy. The Agent, prompt,
parser and H1 sources are verified unchanged directly.

Validator: `validate_model_structured_output_1.py`.

## 7. Next gate

1. The operator runs `uv run python .\validate_model_structured_output_1.py`,
   then commits; the maintainer decides ADR-022 acceptance.
2. **Separately authorized:** a minimal live structured-output compatibility
   probe against the qualified local Ollama runtime. It must be non-semantic,
   use no evaluation content and make one bounded call.
3. **Then:** H2 evidence envelope (Agent 1.1.0), followed by H3 schema
   adoption.

Neither the probe nor H2 is authorized by this slice.

## 8. Local qualification

Operator qualification passed on 2026-10-08 (implementation commit `f3d824d`):
all **63/63 phases** of
`uv run python .\validate_model_structured_output_1.py`.
The run covered:
- the H1 prerequisite and scope against `3916451`;
- ADR-022 recorded and indexed;
- 57 structured-output tests and 50 coverage phases;
- regressions:
  - the full Core suite (1964 passed, 1 pre-existing wheel-inventory test
    deselected);
  - Engineering Agent and analyst (398);
  - ForgeAI H1, evidence loop, SAFETY-LIVE-1 and application tests (248
    passed, 2 superseded proxy assertions deselected);
  - SAFETY-EVAL-2/3 (98) and DocuMind (19);
- the zero-provider check, mypy, Ruff lint and format, and the diff check.

This is offline evidence only, and no provider was contacted. ADR-022 remains
**Proposed** until the maintainer accepts it. Ollama 0.40.0's handling of the
schema is **not live-qualified**: a separately authorized minimal probe is
still required before any Agent adopts structured output.
