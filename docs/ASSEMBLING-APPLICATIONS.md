# Assembling applications on LegoAI

This guide shows how to build a new LegoAI consumer application. It describes
the assembly model this repository has **demonstrated** with three real
consumers:

- **DocuMind**, a governed document Q&A application;
- **engineering consumers**, the examples and `CONSUMING.md` in
  `legoai-engineering`;
- **ForgeAI**, a reviewed repository task worker.

It is a guide to an approach, not a framework API specification. For which
modules exist and how mature each one is, see the
[Module Catalog](modules/MODULE-CATALOG.md).

## 1. Start with application intent

Write down the task before choosing any module:

- what the user asks for;
- what the application returns;
- which **effects** it may cause (model calls, file writes, process runs,
  uploads);
- which **authority** each effect needs.

ForgeAI started from "one bounded coding task on one clean repository,
verified by real checks". Everything else followed from that.

## 2. Define application-owned inputs, outputs and effects

Your application owns its own vocabulary:

- **Inputs** are the domain intent only. ForgeAI's `TaskRequest` holds an
  objective, targets and constraints, and never a model name, URL, grant,
  executable or path to a host directory.
- **Outputs** are a closed result that says what happened. ForgeAI's
  `TaskResult` has a closed disposition, a closed failure reason and bounded
  evidence built from LegoAI result values.
- **Effects** are listed explicitly, each with a failure semantic (nothing
  happened, completed, or unknown) and a retry policy (ForgeAI: none).

## 3. Discover reusable modules

Use the [Module Catalog](modules/MODULE-CATALOG.md). Read each candidate's
maturity label and limitations before relying on it. A **replay-qualified**
or **deterministically qualified** module has not been measured against live
models.

## 4. REUSE > EXTEND > CREATE

Prefer the leftmost option that meets the requirement.

| Choice | Meaning | Real examples |
| --- | --- | --- |
| **REUSE** | Use an existing public capability unchanged | ForgeAI reuses `CodingAgent`, `IndependentReviewer`, the `EngineeringCheckPort` implementations and the public governed host |
| **EXTEND** | Add a new implementation of an **existing** Port, or a decorator over it | CR-2b `SandboxedEngineeringChecks` implements the existing `EngineeringCheckPort`; the CR-3 authorized wrappers decorate `RepositoryMutationPort` and `EngineeringCheckPort` |
| **CREATE in the application** | Write application-specific behavior in your own package | ForgeAI's `TaskRequest`, `TaskResult`/`TaskEvidence`, `WorkspaceGuard`, its fixed run sequence, and its review and rework material rendering |

**The ownership test.** Before proposing anything for LegoAI, ask: *"If this
application disappeared tomorrow, would the abstraction still legitimately
belong in LegoAI?"* If not, it stays in the application.

**The Rule of Two / Rule of Three.** Generalize into LegoAI only after two
independent consumers need the same semantics, and preferably three.
ForgeAI-1/2/3 built a gated, reviewed flow with one bounded rework using
**no new LegoAI platform abstraction**. One application's fixed sequence is
not evidence for a generic Workflow or Team; see the
[direction assessment](../planning/FORGEAI-4-AND-M8.4-DIRECTION.md) §11.

## 5. Separate task input, operator configuration and adapters

| Kind | Who supplies it | Examples |
| --- | --- | --- |
| Runtime or task input | The user, per request | An objective, targets, a question, a document to ingest |
| Operator configuration | The deployment operator | Model bindings and selection, grants, workspace and check policies, the sandbox image from the closed set, provider settings |
| Adapter implementation | Code in your composition root | Which concrete adapter implements each Port |

**LegoAI is not "everything through configuration".**

Configuration can select supported variation, such as:

- an admitted model binding;
- grants;
- policies;
- a qualified sandbox image;
- supported provider settings.

Code is still required for:

- application workflow and domain behavior;
- adapters for unsupported providers;
- new semantic capabilities;
- composition roots, since no generic configuration loader exists.

## 6. Compose through public entry points

Applications use only:

- public owner values and Ports (for example `legoai.execution.agent`,
  `legoai.governance.ports`, and the engineering `ports`/`values` modules);
- `legoai.runtime.api`, the host configuration types and `GovernedHost`;
- `legoai.runtime.local.open_local_host`, called **only** in the composition
  root;
- documented package APIs (engineering `CONSUMING.md`, and the other package
  READMEs linked from the catalog).

Applications never use:

- `legoai.reference.*`;
- `legoai.runtime._composition.*`;
- any underscore-prefixed module or name, including private engineering
  wiring;
- provider SDKs in domain code.

A minimal composition root, where operator configuration is passed in:

```python
from legoai.runtime.api import GovernedHost, LocalHostConfig, ModelPurpose
from legoai.runtime.local import open_local_host


def open_application(config: LocalHostConfig, selection: dict[str, object]) -> GovernedHost:
    # Operator configuration in, one governed host out. Task data never
    # reaches this function.
    host = open_local_host(config, selection)
    host.model_execution(ModelPurpose.CHAT)  # a fresh governed Chat context
    return host
```

## 7. Keep concrete adapters in the composition root

**Only the composition root** imports local adapters (`*.local`,
`sandbox.docker`, `checks.sandboxed`, `mutation_local`, `git.local`) and
opens the host. Domain and application modules depend only on Ports and
values. ForgeAI enforces this with an architecture test: its composition
module is the only one allowed to import adapters.

## 8. Keep domain code on public Ports and values

The ForgeAI worker depends on:

- `GitRepositoryPort`, `RepositoryMutationPort` and `EngineeringCheckPort`;
- `CodingAgent`, `IndependentReviewer` and `RepositoryEvidencePort`;
- values.

It never touches the filesystem, subprocesses, the model Port or the host
directly. Swapping an adapter changes only the composition root.

## 9. Add authorization at effect boundaries

- **Model text grants no authority.** Proposals, reviews and findings are
  data.
- **Governed model calls** are authorized by the host (`invoke-capability`).
- **Repository reads disclosed to a model** need `read-for-model-analysis`,
  through `AuthorizedRepositoryEvidence` (or `AuthorizedCodingEvidence`).
- **Writes** go through `AuthorizedRepositoryMutation`
  (`apply-repository-changes`). **Checks** go through
  `AuthorizedEngineeringChecks` (`run-engineering-check`). Current authority
  is checked immediately before every effect, and a denial means no effect.
- **Contexts come from the host.** Obtain a `SecurityContext` from
  `host.security_context(...)`. Never construct a `Grant` or
  `SecurityContext` yourself.
- **Approval-bearing engineering contexts currently fail closed.**
- **Local host grants are volatile,** single-operator local authority, not
  IAM.
- **Git is operator-only in ForgeAI.** No authorized boundary exists for
  disclosing Git data to a model.
- **Sandbox is containment, not integrity.** `SandboxedEngineeringChecks`
  contains untrusted code, but a pass is only a contained observation, not
  proof of correctness.

## 10. Test with fakes and replay before live providers

- **Fake `ModelPort` contributions.** Use a `TrustedModelContribution` that
  returns recorded outputs, like ForgeAI's replay model or the engineering
  examples' static model.
- **Fake Ports** for Git, mutation, checks and the sandbox, to inject
  failures.
- **Real adapters** for the effects you claim, such as real Docker checks in
  ForgeAI's end-to-end tests.
- **Governance negatives** to keep: denied, expired, revoked, unavailable,
  approval-bearing and wrong-scope contexts.

## 11. Add clean-install and public-import architecture tests

- **Clean install:** build your wheel and LegoAI's wheels, install them
  offline into a fresh environment, and run your example outside the
  checkout, as ForgeAI's `test_clean_install.py` does.
- **Public imports:** adapt this recipe to fail on private imports in your
  package.

```python
import ast
from pathlib import Path


def private_imports(package: Path) -> list[str]:
    found = []
    for path in package.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module:
                parts = node.module.split(".")
                if node.module.startswith(("legoai.reference", "legoai.runtime._composition")) or (
                    parts[0].startswith("legoai") and any(p.startswith("_") for p in parts)
                ):
                    found.append(f"{path.name}: {node.module}")
    return found
```

## 12. Record qualification honestly

| Kind | What it proves | Example |
| --- | --- | --- |
| Deterministic qualification | Contracts and flows hold under fakes | The engineering Agent tests, with fake models |
| Real-tool / live qualification | A real provider or tool behaved as specified in the stated scope | M5/M6 on real Git, filesystem and Docker; DocuMind v0.1 with local Ollama |
| Replay-model application qualification | The application's architecture, governance and flow work with recorded model outputs and real tools | **ForgeAI-3**: flow, authorization, sandboxed checks, review and one rework, qualified with replay models and real Docker |
| Live-model behavioral evaluation | How real models actually perform on frozen tasks | **ForgeAI-LQ1** (planned, not implemented): a measurement harness with hidden acceptance tests |

Do not merge these. ForgeAI-3's qualification says nothing about how well a
live model codes or reviews.

## 13. Promote patterns to LegoAI only with reuse evidence

A pattern moves from an application into LegoAI only when:

- it passes the ownership test;
- at least two consumers need the same semantics;
- the change is REUSE or EXTEND of existing contracts where possible;
- an ADR records any significant architecture decision.

## Worked examples

### A. DocuMind: governed document Q&A

```
DocuMind configuration (operator)
  → open_local_host (public host; chat and embedding grants)
  → governed_chat / governed_embed callables
  → legoai-document ingestion, retrieval and answering (injected callables)
  → DocuMind CLI workflow (ingest, ask, status)
```

- **LegoAI owns:** the governed host and model calls, and the document pack's
  parsing, chunking, embedding, ingestion, retrieval, rerank and answering
  logic.
- **DocuMind owns:** its configuration, its composition root
  (`composition.py`), the CLI and its local SQLite store location.

DocuMind never sees the Catalog, Coordinator, registries or provider
adapters. See the [DocuMind README](../examples/documind/README.md).

### B. Engineering consumer: authorized repository changes

```
public host → security contexts per action
  → AuthorizedRepositoryEvidence → CodingAgent / RepositoryAnalyst / IndependentReviewer
  → AuthorizedRepositoryMutation (writes)
  → AuthorizedEngineeringChecks → LocalEngineeringChecks or SandboxedEngineeringChecks
```

Choose the check adapter by trust:

| Adapter | Use for |
| --- | --- |
| `LocalEngineeringChecks` | **Trusted** local code; it runs as the host user |
| `SandboxedEngineeringChecks` | Model- or repository-controlled code that needs containment; there is no host fallback |

See the [engineering consumer guide](../packages/legoai-engineering/docs/CONSUMING.md)
for the full, public-imports-only composition.

### C. ForgeAI: an application assembled without new platform abstractions

```
ForgeAI-owned: TaskRequest → RepositoryTaskWorker (fixed sequence) → TaskResult / TaskEvidence
reused LegoAI: public host, CodingAgent, IndependentReviewer, authorized reads,
               AuthorizedRepositoryMutation, AuthorizedEngineeringChecks,
               SandboxedEngineeringChecks, GitRepositoryPort
```

ForgeAI-1/2/3 required **no new LegoAI platform abstraction**:

- the fixed sequence is ForgeAI's own: clean-start gate, propose, apply,
  check, Git integrity check, review, and at most one rework;
- `WorkspaceGuard` and the review and rework rendering are ForgeAI's own;
- every effect goes through existing LegoAI wrappers and Ports.

**Current limits:**
- at most 4 model calls, 2 applies, 2 check batches and 2 reviews;
- no rollback;
- target files are operator-supplied;
- replay-only model qualification.

See the [ForgeAI README](../examples/forgeai/README.md).
