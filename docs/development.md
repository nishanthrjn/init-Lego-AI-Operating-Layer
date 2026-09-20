# F0 developer workflow

This is an identity/package foundation, not an executable Lego AI runtime.
It implements Gate-1 F0 under ADR-001/002. No F1 concepts or persistence exist.

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

Wheel runtime content is exactly the two inert initializers, `kernel/identity.py`
and `py.typed`, plus packaging metadata. The sdist deliberately includes the
three test files and this guide so source verification can be reproduced;
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

Tests derive from F0 and ADR-002: validation/immutability/nominal distinction,
strict typing in both directions, import policy negative graphs, inert imports
and installed artifacts. Invalid typing examples are generated only in temporary
directories and checked for the exact two mypy argument diagnostics.

The static checker parses source without executing synthetic fixtures. It checks
Kernel owner boundaries, non-stdlib imports, test imports, star/dynamic imports,
cycles and inert initializers, including imports inside TYPE_CHECKING and helper
re-exports. It is a small development check, not analysis of every possible Python
reflection trick or the full future ADR-002 owner matrix.

The inert-import subprocess preloads stdlib dependencies, disables bytecode
writes, rejects non-code file access/write and network/process/database audit
events, and guards thread startup, environment reads and logging configuration.
It checks remaining threads/log handlers/modules and an unchanged temporary
directory. This observes the F0 import interval; it is not a hostile-code sandbox.

One local `noqa: B010` permits `setattr` in the immutability test to exercise runtime
rejection without inserting a deliberately invalid assignment into strict typing.
Wrong-type runtime tests use a narrow `cast` to cross the annotated boundary.
There are no broad typing ignores, skipped future tests or external SDKs.

## Verification record

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
