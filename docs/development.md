# Foundation developer workflow

This is an identity/package foundation, not an executable Lego AI runtime.
It implements Gate-1 F0/F1 under ADR-001–005/008. No F2 composition,
persistence, authority engine or executable runtime exists.

## Environment and dependencies

Local verification uses conventional GIL-enabled CPython **3.14.5** on Windows
x86-64 and **uv 0.11.19**. `.python-version` pins that patch; metadata permits
Python `>=3.14,<3.15`. Other patches/platforms are not claimed tested.
Install the specified interpreter and uv through an approved distribution;
installer commands themselves are outside the verification recorded here.

The packaging-only version is `0.1.0.dev0`. Runtime dependencies: **zero**.
Direct development/build requirements are Hatchling 1.32.3, editables 0.5,
pytest 9.1.1, mypy 2.3.1 and Ruff 0.16.8. `editables` is Hatchling's required
editable-build helper, explicitly installed because build isolation is disabled.
It is not a runtime dependency of the built wheel.

The 12 transitive packages are ast-serialize, colorama, iniconfig, librt,
mypy-extensions, packaging, pathspec, pluggy, pygments, tomlkit,
trove-classifiers and typing-extensions. They belong to the selected build,
test or typing tools; none is an application/provider dependency. In particular,
pluggy is pytest's own dependency, not an added pytest plugin.

`uv.lock` records exact resolved packages and PyPI artifact hashes. Review it
when dependencies change. Resolution and successful tests are not a security
audit, publisher authentication or a vulnerability-free claim. No hidden Git,
editable third-party, alternate-index or provider dependencies are intended.

## Commands

Run from the repository root. Initial lock creation was performed with `uv lock`;
ordinary checking uses `--locked` and does not update dependencies.

```text
uv sync --locked --group dev --no-install-project
uv sync --locked --group dev --no-build-isolation
uv run --locked --no-sync python -m pytest
uv run --locked --no-sync python -m mypy src tests
uv run --locked --no-sync ruff check .
uv run --locked --no-sync ruff format --check .
uv build --no-build-isolation
git diff --check
```

The two-stage sync installs the pinned build dependencies before building the
editable project. The non-isolated build uses that prepared environment instead
of independently resolving backend dependencies. A local cache on another drive
may cause uv to fall back from hardlinks to copying; that does not alter the lock.

For formatting edits, use `uv run --locked --no-sync ruff format src tests`.
There is no extra task runner or public CLI.

The full pytest command builds both wheel and sdist into a temporary directory,
checks their exact file inventories, creates a fresh stdlib venv without pip,
installs the wheel with `uv pip install --python <fresh-python> --no-deps --offline
<wheel>`, and runs an isolated import outside the checkout. The generated-path
commands are executed by the test; no `sys.path` edits are used. Repeat that check:

```text
uv run --locked --no-sync python -m pytest tests/architecture/test_package_install.py
```

Wheel runtime content is the three inert initializers, six Kernel modules,
`governance/values.py` and `py.typed`, plus packaging metadata. The sdist includes
the five test files and this guide so source verification can be reproduced;
tests are not wheel runtime content. It also contains Hatchling's included
`.gitignore`. No caches, planning documents, database or credentials belong in
either artifact. Build outputs and generated test bytecode remain ignored.

## Identity input and public surface

Import from `legoai.kernel.identity`; the root package does not re-export values.
`TenantId` and `PrincipalId` are distinct frozen, slotted dataclasses containing
exact built-in `str` values of 1–256 Unicode code points. Non-text (including str
subclasses), empty and over-bound representations fail explicitly. Case,
whitespace and Unicode spelling are preserved, including whitespace-only text.
No canonical UUID rule is imposed. The bound is implementation protection, not
identity semantics or resource entitlement.

Same-kind equality/hash use the exact text. Different kinds remain unequal even
with identical text; equal hashes across kinds would be legal and do not imply
equal identities. `repr` omits the value; accessing `.value` still discloses it.
Neither identity is a credential, verified Principal, TenantContext or grant.
Frozen dataclasses prevent normal assignment, not hostile reflective Python
mutation; no in-process security isolation is claimed.

## Verification boundaries

Tests derive from F0/F1 and ADR-002: validation/immutability/nominal distinction,
strict typing in both directions, import policy negative graphs, inert imports
and installed artifacts. Invalid typing examples are generated only in temporary
directories and checked for two F0 and six F1 expected mypy argument diagnostics.

The static checker parses source without executing synthetic fixtures. It checks
Kernel and Governance value boundaries, non-stdlib imports, test imports,
star/dynamic imports,
cycles and inert initializers, including imports inside TYPE_CHECKING and helper
re-exports. It is a small development check, not analysis of every possible Python
reflection trick or the full future ADR-002 owner matrix.

The inert-import subprocess preloads stdlib dependencies, disables bytecode
writes, rejects non-code file access/write and network/process/database audit
events, and guards thread startup, environment reads and logging configuration.
It checks remaining threads/log handlers/modules and an unchanged temporary
directory. This observes all F0/F1 module imports; it is not a hostile-code sandbox.

Local `noqa: B010` markers permit `setattr` in immutability tests to exercise runtime
rejection without inserting a deliberately invalid assignment into strict typing.
Wrong-type runtime tests use local `cast` calls to cross the annotated boundary.
Negative dataclass replacement cases cast the callable to `Callable[..., object]`
only at the deliberately invalid call; production constructors stay strictly typed.
There are no broad typing ignores, skipped future tests or external SDKs.

## F1 semantics and boundaries

- `kernel.identity` adds ApplicationId, OperationId, RequestId, CorrelationId and
  TraceId with the same exact-text, nominal and immutable F0 contract.
- `kernel.references` defines ReferenceScope (owner + tenant), PrincipalRef
  (identity issuer + PrincipalId), ApplicationRef/ApplicationRevisionRef,
  ConfigurationRef/ConfigurationRevisionRef and OperationRef. Record classes
  distinguish concepts. Operation references additionally identify contract and
  typed subject; raw operation IDs cannot collapse across those scopes.
  Configuration instance text is a locator component, not the F2 owned instance
  value. This first configuration reference profile requires the Application
  scope selected by the accepted persistence plan; it does not create an
  Application entity. Application-free configurations remain unsupported in this
  profile rather than being represented with a fabricated Application identity.
- ConfigurationRevisionRef pins an opaque revision and its interpretation Version.
  OwnerRevision instead pairs a typed ConfigurationRef (owner/tenant/Application/
  instance) with a positive exact integer equality guard. Other mutable subject
  kinds await actual consumers. It offers no ordering, allocation or successor
  method. The later storage boundary must enforce its own integer storage range;
  this primitive does not impose SQLite semantics. Neither reference proves that
  its asserted owner issued a record or that the record is accessible.
- `kernel.versions.Version` supports only exact nonnegative integer release
  triples and lexicographic ordering (CTR-064). Booleans, coercion, text parsing,
  ranges and prerelease arguments are rejected. F1 has no prerelease consumer;
  an explicitly shared prerelease interpretation must precede admitting one in
  later declaration matching. Ordering never establishes compatibility, including
  between 0.x versions. Distribution version `0.1.0.dev0` remains packaging-only.
- `kernel.context.TenantContext` contains exactly one explicit TenantId.
  `governance.values.Principal` contains an issuer-scoped PrincipalRef, with no
  verification status or grants. Governance's OperationContext composes those
  values with scoped operation, request/correlation/trace IDs and explicit
  root-or-causation. This placement avoids Kernel importing Governance. All
  arguments are required; `causation=None` explicitly denotes root and
  `trace_id=None` requests eventual receiver assignment. Cross-tenant causation
  and self-causation are rejected in this initial local subset.
- Contexts are synthetic non-delegated administrative inputs. Actor and requester
  must match; delegated contexts are explicitly unsupported until their reference
  contract is implemented. No F1 consumer waits, so deadlines and clock semantics
  are deferred to the first waiting boundary. Owner-specific requests will supply
  their contract/version and pinned governing Application/configuration inputs
  when applicable. This anchor is neither ExecutionContext nor a complete
  operational common envelope; omission cannot authorize live operation.
- `kernel.errors` contains the five initial ErrorCategory values, independent
  Recoverability, ErrorCause and ErrorDetail. The latter is a classification/cause
  component, **not a complete CTR-011 error result**. Immutable cause tuples retain
  primary and secondary references. Later owner result contracts supply the
  remaining required attribution, safe diagnostics, observation time, named
  effects and conditional retry constraints. No category implies retry or effect.
- `kernel.effects.EffectExtent` contains exactly none/partial/completed/unknown.
  It does not identify an effect or encode success, Execution state or recovery.

Constructors raise local TypeError for wrong types and ValueError for invalid
values/combinations. These exceptions are not canonical error outcomes and their
raw text/tracebacks must not be used as such. Reference text uses the same local
1–256 code-point protection as IDs; no UUID, trimming or canonical string grammar
is imposed. Repr omits opaque strings; it is not a serialization contract or a
data-disclosure control. Cause/reference accessibility still requires owner checks.

All records are frozen and slotted with exact nested type checks; tuples contain
only validated immutable cause records. No ambient context, module state,
credentials, I/O, lookup, policy evaluation, codecs or runtime dependencies were
added. These representations cannot authenticate, authorize or admit an operation.

## F0 verification record

Verified on 2026-09-21 in the environment above: both locked sync commands;
49 pytest cases; strict mypy over all six source/test modules; Ruff check and
format check; wheel and sdist builds; fresh offline wheel installation and
isolated import; and `git diff --check`. The targeted package-test command was
also exercised. The interpreter reported its GIL enabled.

Dependency review found 5 direct development/build packages and 12 transitive
packages, all resolved from PyPI with artifact hashes; the only editable entry
is this project. Direct-tool installed metadata declares MIT licensing. This is
an inventory and purpose review, not a comprehensive license/security approval
or vulnerability scan. No unexpected runtime dependencies were found.

The implementation review was a separate pass by the same assistant against
ADR-001/002 and the F0 task, not independent third-party assurance. No canonical
documents changed. No Conformance, runtime, release-publication or
production-readiness claim follows from F0.

## F1 verification record

Verified on 2026-09-21 using the same CPython 3.14.5 environment: **96 pytest
cases passed**, including F0 regressions, negative architecture/typing fixtures,
all-module inert imports and fresh offline wheel installation outside the
checkout. Strict mypy passed all **15 source/test modules**. Ruff check and
format check passed; wheel and sdist built with `uv build --no-build-isolation`.
Artifact tests enforce exact inventories, the typing marker and zero runtime
requirements. `git diff --check` passed. Build/tool configuration and lockfile
are unchanged. No dependencies, accepted decisions or F2 behavior were added.

The same-assistant adversarial review checked subject-scoped operation identity,
non-authoritative context, nominal/equality separation, immutable nested values,
validation/coercion, dependency direction, synthetic fixture paths and packaged
content. F1 is a representation foundation, not security isolation or operational
Conformance evidence. Prereleases, delegation and waiting/deadline behavior remain
explicitly unsupported until their consuming contracts require them.
