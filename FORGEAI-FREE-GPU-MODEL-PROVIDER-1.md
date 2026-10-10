# FORGEAI-FREE-GPU-MODEL-PROVIDER-1

Current closeout status: **FULL VALIDATION PENDING**. See
[the closeout report](FORGEAI-FREE-GPU-MODEL-PROVIDER-1-CLOSEOUT.md) for the
corrected approval caller, canonical synthetic contracts, and current failures.
The implementation record below describes the earlier validation attempt.

Implemented; scoped offline validation passed. Full regression validation is
not complete: the attempted full ForgeAI suite has legacy/environment blockers.
No commit, live provider call, tunnel, paid service or runtime deployment occurred.

1. **Contracts reused.** ModelPort, ChatRequest/ChatResult, OpenAICompatibleSettings,
   ModelBindingConfig, LocalHostConfig, governed_chat, RemoteDisclosureConfig,
   ExecutionDisclosure, CredentialSource, RemoteModelRuntime, and the existing
   bounded RepositoryWorkspacePort/LocalRepositoryWorkspace.
2. **Files changed.** Exact worktree file list appears below.
3. **Public additions.** ModelFailure (closed safe facts), optional failure on
   governed chat and Model exceptions, and optional deterministic OpenAI settings.
   Defaults preserve existing requests. No ModelPort, ChatRequest, ChatResult or
   Agent shape changes. Application-only ProviderProfile/ProviderSession and
   bounded evidence/approval values are documented in ADR-025. The inability of
   existing contracts to express deterministic sampling and distinguish failures
   was explained before implementation.
4. **Configuration.** provider_type=openai_compatible; exact base_url/model;
   explicit local/remote mode; provider identity; timeout 1..300 seconds; local
   auth_mode=none or remote auth_mode=secret_source; existing disclosure and
   custody policies. CLI is `python -m forgeai.provider_cli`; examples are in
   examples/forgeai/README.md.
5. **Synthetic flow.** Three fixed calls: READY, exact JSON object, AST-equivalent
   add function. Temperature zero, max_tokens=512, stream=false. No generated
   code execution. Stop on first failure; no retry/fallback. Exact configured
   response model and finish_reason are checked by the existing adapter. This
   proves session interoperability, not quality, deterministic implementation
   or native schema support.
6. **Disclosure.** A synthetic-only policy cannot admit repository content. After
   synthetic success, one separate file approval is required; remote governance
   independently checks the repository classes and recipient on each invocation.
   Existing one-hour admission ceiling and Secret/attempt custody are preserved.
7. **Read-only task.** Summarize one explicitly selected source file in one stable
   local repository, maximum 16 KiB UTF-8. No listing, recursive acquisition,
   implicit context or mutation. The operator must select appropriate content;
   there is no secret-scanning or hostile-filesystem isolation claim.
8. **Tests.** Loopback HTTP plus synthetic TLS cover local no-auth, remote Secret
   custody, separate approval, exact model, config/timeout bounds, request shape,
   failure classification, no retry, response bounds, no secret in evidence,
   excluded/missing/oversized/traversal targets and CLI sequencing. Architecture
   checks forbid agent/mutation/sandbox/Git construction on this entry path.
9. **Validation results (2026-10-10).**
   - New provider + ForgeAI architecture: 73 passed (final CLI refinement included).
   - Full Core regression including architecture/package checks: 2541 passed.
   - Existing ForgeAI remote synthetic TLS regression: 42 passed, 2 real-Docker
     cases intentionally deselected in the scoped validator.
   - Reused Engineering repository/workspace/architecture: 170 passed, 1 POSIX-only
     test skipped on Windows.
   - Strict mypy: 15 Core/change targets and 27 ForgeAI files passed. The legacy
     integration test altered only to assert the new settings field is executed
     and linted, not newly claimed as a strict-mypy-clean test module.
   - Ruff check, format check and git diff --check passed.
   - validate_forgeai_free_gpu_model_provider_1.py completed successfully.
   - Full ForgeAI regression was attempted and failed. Independently reproduced
     blockers: Docker Desktop Linux engine named pipe is absent; the existing
     evaluation runner calls run_task without its required approve argument.
     Both sides of that signature mismatch were confirmed in HEAD. No blanket
     claim that every full-suite failure has been repaired or independently
     attributed is made. Use --full after restoring the legacy prerequisites.
10. **No infrastructure coupling.** Core has no Kaggle identifier (source search
    returned no matches). Production ForgeAI imports only public LegoAI contracts
    and existing composition adapters. Runtime qualification evidence is not
    endpoint availability; notebooks are not assumed always-on or reachable.
11. **No mutation.** The new host grants chat and, remotely, exact Secret use only;
    four execution slots, no mutation/check capability. The read-only path never
    constructs CodingAgent, mutation, Git or Docker. File snapshot tests confirm
    no repository changes. Output is bounded untrusted text, never applied.
12. **Next slice.** Restore the legacy full-regression baseline, then separately
    authorize live synthetic provider and read-only/disclosure qualification
    against an available endpoint. Mutation remains later.
13. **Proposed commit.** `feat(forgeai): add governed synthetic-first provider qualification`

## Reproduce

From the repository root:

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_free_gpu_model_provider_1.py
if ($LASTEXITCODE -ne 0) { throw 'Provider slice validation failed' }
# Requires the existing qualified Docker setup and corrected legacy evaluation baseline:
uv run --locked --offline --no-sync python .\validate_forgeai_free_gpu_model_provider_1.py --full
if ($LASTEXITCODE -ne 0) { throw 'Full provider regression failed' }
```

## Changed files

- `FORGEAI-FREE-GPU-MODEL-PROVIDER-1.md`
- `README.md`
- `adrs/ADR-025.md`
- `examples/forgeai/README.md`
- `examples/forgeai/src/forgeai/composition.py`
- `examples/forgeai/src/forgeai/provider.py`
- `examples/forgeai/src/forgeai/provider_cli.py`
- `examples/forgeai/src/forgeai/remote.py`
- `examples/forgeai/tests/test_architecture.py`
- `examples/forgeai/tests/test_clean_install.py`
- `examples/forgeai/tests/test_provider.py`
- `src/legoai/intelligence/model/ports.py`
- `src/legoai/intelligence/model/values.py`
- `src/legoai/reference/_credential_https.py`
- `src/legoai/reference/model_openai_compatible.py`
- `src/legoai/runtime/_composition/agent.py`
- `src/legoai/runtime/_composition/credential_https.py`
- `src/legoai/runtime/_composition/model_governed.py`
- `src/legoai/runtime/_composition/remote_model.py`
- `src/legoai/runtime/api.py`
- `src/legoai/runtime/local.py`
- `tests/architecture/test_local_host.py`
- `tests/architecture/test_package_install.py`
- `tests/architecture/test_remote_disclosure.py`
- `tests/integration/composition/test_openai_compatible.py`
- `tests/unit/reference/test_model_provider_diagnostics.py`
- `validate_forgeai_free_gpu_model_provider_1.py`
