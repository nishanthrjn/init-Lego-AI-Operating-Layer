"""Attended fixed-fixture pilot; no admitted model is shipped with this slice."""

import asyncio
import hashlib
import json
import shutil
import sys
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from demo import FIXTURE, OBJECTIVE, TARGETS, create_repository
from legoai.runtime.api import OpenAICompatibleSettings, RemoteModelRuntime
from legoai_engineering.coding.values import CodingTarget
from legoai_engineering.repository.mutation import FileChangeKind
from legoai_engineering.repository.workspace import RepositoryPath
from legoai_engineering.sandbox.ports import SandboxExecutionPort

from forgeai.cli import (
    remote_confirmer,
    terminal_approver,
    terminal_context_confirmer,
)
from forgeai.composition import (
    ForgeAIConfig,
    bind_remote,
    local_profile,
    prepare_run,
    remote_credentials,
    sandbox_readiness,
)
from forgeai.domain import TaskDisposition, TaskRequest, TaskResult
from forgeai.guard import WorkspaceGuard
from forgeai.remote import BINDING, RemoteProfile, load_profile, task_digest
from scripts.kisski_saia_qualification import discover_models

VERSION = "FORGEAI-V0.2-KISSKI-BOUNDED-LIVE-PILOT-1"
AUTHORIZATION = "AUTHORIZE " + VERSION + " LIVE DISPOSABLE REPOSITORY"
ENDPOINT = "https://chat-ai.academiccloud.de/v1"
PROVIDER = "kisski-saia"
FIXTURE_ID = "stock_task"
FIXTURE_DIGEST = "cfbdb41a535c31fb22d4219d34f26c72a644e965e267e6f2197c7c6e0e3465de"
OUTPUT_TOKENS = 1024
CONTEXT = (RepositoryPath("pyproject.toml"),)


@dataclass(frozen=True)
class Admission:
    """Reviewed source-controlled evidence, never CLI/config/model authority.

    Adding a row requires a new maintainer review and local qualification.
    Evidence references identify complete runs, not merged partial results.
    """

    model: str
    connectivity: str
    structured_smoke: str
    quality_review: str
    protocol_clear: bool
    output_tokens: int


# No candidate satisfies the reviewed admission rule. No operator override.
ADMISSIONS: tuple[Admission, ...] = ()


def admitted(model: str, discovered: tuple[str, ...]) -> bool:
    rows = [row for row in ADMISSIONS if row.model == model]
    return (
        len(rows) == 1
        and model in discovered
        and bool(rows[0].connectivity)
        and bool(rows[0].structured_smoke)
        and bool(rows[0].quality_review)
        and rows[0].protocol_clear is True
        and rows[0].output_tokens == OUTPUT_TOKENS
    )


def task() -> TaskRequest:
    return TaskRequest(
        OBJECTIVE,
        tuple(CodingTarget(RepositoryPath(p), FileChangeKind.UPDATE) for p in TARGETS),
        ("Keep the public function signature unchanged.",),
        CONTEXT,
    )


def fixture_digest() -> str:
    """Only initial repository files; never read recorded solutions or reviews."""
    root = FIXTURE / "repository"
    if root.is_symlink() or any(p.is_symlink() for p in root.rglob("*")):
        raise ValueError("fixture links refused")
    files = sorted(path for path in root.rglob("*") if path.is_file())
    material = [(p.relative_to(root).as_posix(), p.read_text("utf-8")) for p in files]
    return hashlib.sha256(json.dumps(material, ensure_ascii=True).encode()).hexdigest()


def plan() -> dict[str, object]:
    # No filesystem reads, credentials, discovery or Docker in plan mode.
    return {
        "pilot_id": VERSION,
        "fixture": FIXTURE_ID,
        "fixture_digest": FIXTURE_DIGEST,
        "task": OBJECTIVE,
        "targets": TARGETS,
        "context": [p.value for p in CONTEXT],
        "endpoint": ENDPOINT,
        "admissible_models": [row.model for row in ADMISSIONS],
        "admission": "PILOT_MODEL_NOT_ADMITTED" if not ADMISSIONS else "REVIEWED",
        "max_discovery": 1,
        "max_chat": 4,
        "max_provider_calls": 5,
        "output_tokens": OUTPUT_TOKENS,
        "timeout_seconds": 60,
        "authorization": AUTHORIZATION,
        "scope": "GENERIC PYTHON_CHECKS; one rework; no retry/fallback",
    }


def projection(result: TaskResult) -> dict[str, Any]:
    """Closed enums/booleans/counts only; never serialize TaskEvidence wholesale."""
    evidence = result.evidence
    attempts = []
    for item in evidence.attempts:
        reviewer = item.review
        agent = reviewer.agent_result if reviewer else None
        attempts.append(
            {
                "number": item.number,
                "coding_status": item.coding_status.name
                if item.coding_status
                else None,
                "model_attempt": item.agent_status.name if item.agent_status else None,
                "model_effect": item.model_effect.name if item.model_effect else None,
                "proposal_valid": item.proposal is not None,
                "mutation_approval": item.approval,
                "applied_count": len(item.applied.applied) if item.applied else 0,
                "mutation_uncertain": item.uncertain is not None,
                "mutation_denied": item.mutation_denial is not None,
                "mutation_conflict": item.conflict is not None,
                "checks": [
                    {
                        "kind": check.request.kind.name,
                        "outcome": check.result.outcome.name if check.result else None,
                        "no_result": check.result is None,
                    }
                    for check in item.checks
                ],
                "review_status": reviewer.status.name if reviewer else None,
                "review_decision": (
                    item.review_decision.name if item.review_decision else None
                ),
                "review_effect": (
                    agent.model_execution.effect.name
                    if agent and agent.model_execution
                    else None
                ),
            }
        )
    return {
        "status": (
            "PILOT_SUCCEEDED"
            if result.disposition is TaskDisposition.SUCCEEDED
            else "PILOT_" + result.failure.name
            if result.failure
            else "PILOT_RESULT_INCONCLUSIVE"
        ),
        "run_id": evidence.run_id,
        "task_disposition": result.disposition.name,
        "task_failure": result.failure.name if result.failure else None,
        "context_confirmed": evidence.context_confirmed,
        "context_decisions": [c.confirmed for c in evidence.context_confirmations],
        "rework_used": evidence.reworked,
        "attempts": attempts,
        "changes_retained": any(item.applied is not None for item in evidence.attempts),
        "repository_effect": (
            "UNKNOWN"
            if any(item.uncertain is not None for item in evidence.attempts)
            else "KNOWN"
            if any(item.applied is not None for item in evidence.attempts)
            else "NONE"
        ),
        "rollback_performed": False,
    }


async def execute_task(
    config: ForgeAIConfig,
    *,
    ask: Callable[[str], str],
    write: Callable[[str], None],
    sandbox: SandboxExecutionPort | None = None,
) -> dict[str, Any]:
    """One public ForgeAI lifecycle on one event loop; substitution is test-only."""
    disclosure: bool | None = None
    confirm = remote_confirmer(ask, write)

    def disclose(preview: str) -> bool:
        nonlocal disclosure
        write("repository identity: " + FIXTURE_ID)
        write("task identity: " + task_digest(task()))
        disclosure = confirm(preview)
        return disclosure

    prepared = prepare_run(
        config,
        WorkspaceGuard(),
        approve=terminal_approver(ask, write),
        confirm_context=terminal_context_confirmer(ask, write),
        confirm_disclosure=disclose,
        sandbox=sandbox,
    )
    result = await prepared.worker.run(task(), prepared.context)
    report = projection(result)
    report["disclosure_approved"] = disclosure
    return report


def check_profile(profile: RemoteProfile, model: str) -> None:
    if (
        profile.base_url != ENDPOINT
        or profile.provider.value != PROVIDER
        or profile.model != model
        or profile.repository.value != FIXTURE_ID
    ):
        raise ValueError("pilot profile mismatch")
    profile.validate(datetime.now(UTC))


def run_attended(ask: Callable[[str], str], write: Callable[[str], None]) -> int:
    """Called only after terminal and exact authorization checks by main."""
    if not ADMISSIONS:
        write("PILOT_MODEL_NOT_ADMITTED; no credentials or provider calls")
        return 1
    model = ask("Exact reviewed model ID (no aliases or quotation marks): ")
    if not admitted(model, (model,)):
        write("PILOT_MODEL_NOT_ADMITTED")
        return 1
    # Strict existing non-secret policy schema; never synthesize provider facts.
    profile = load_profile(Path(ask("Existing non-secret disclosure profile TOML: ")))
    check_profile(profile, model)
    if fixture_digest() != FIXTURE_DIGEST:
        write("PILOT_FIXTURE_INVALID")
        return 1
    git, docker = shutil.which("git"), shutil.which("docker")
    if git is None or docker is None:
        write("PILOT_SANDBOX_FAILED; existing Git and Docker required")
        return 1
    retained = Path(tempfile.mkdtemp(prefix="forgeai-kisski-pilot-"))
    write("retained pilot directory: " + str(retained))
    report: dict[str, Any] = {
        "pilot_id": VERSION,
        "model": model,
        "task_id": task_digest(task()),
        "fixture_id": FIXTURE_ID,
        "fixture_digest": FIXTURE_DIGEST,
        "provider": PROVIDER,
        "endpoint": ENDPOINT,
        "sandbox_profile": "GENERIC/PYTHON_CHECKS",
        "output_tokens": OUTPUT_TOKENS,
        "maximum_provider_calls": 5,
        "context_confirmed": None,
        "disclosure_approved": None,
        "attempts": None,
        "task_disposition": None,
        "task_failure": None,
        "status": "PILOT_RESULT_INCONCLUSIVE",
        "effect": "UNKNOWN",
        "repository_effect": "NONE",
        "rollback_performed": False,
    }
    started = time.monotonic()
    try:
        cfg = local_profile(
            retained / "repository",
            tuple(RepositoryPath(p) for p in TARGETS),
            bindings=(profile.binding(),),
            binding=BINDING,
            git_executable=Path(git),
            docker_executable=Path(docker),
            now=datetime.now(UTC),
            context_paths=CONTEXT,
        )
        if sandbox_readiness(cfg) is not None:
            report.update(status="PILOT_SANDBOX_FAILED", effect="NONE")
            return 1
        discovery_custody = retained / "discovery"
        discovery_custody.mkdir()
        discovered = discover_models(discovery_custody)
        if discovered is None:
            report["status"] = "PILOT_DISCOVERY_FAILED"
            return 1
        if not admitted(model, discovered):
            report["status"] = "PILOT_MODEL_NOT_ADMITTED"
            return 1
        write(json.dumps({"model": model, "endpoint": ENDPOINT, "task": plan()}))
        if ask("Approve this one disposable repository live phase? [y/N] ") != "y":
            report["status"] = "PILOT_DISCLOSURE_DECLINED"
            return 1
        create_repository(cfg.repository, Path(git))
        # No task output is ever committed; only the initial demo baseline.
        custody = retained / "model"
        custody.mkdir()
        source = remote_credentials(cfg)
        try:
            cfg = bind_remote(
                cfg,
                replace(profile, timeout=60),
                task(),
                RemoteModelRuntime(source, custody, timedelta(seconds=5)),
                now=datetime.now(UTC),
            )
            binding = cfg.host.bindings[0]
            settings = binding.provider
            assert isinstance(settings, OpenAICompatibleSettings)
            binding = replace(
                binding, provider=replace(settings, max_output_tokens=OUTPUT_TOKENS)
            )
            cfg = replace(
                cfg, host=replace(cfg.host, bindings=(binding,), max_executions=4)
            )
            report["repository_effect"] = "UNKNOWN"
            report.update(asyncio.run(execute_task(cfg, ask=ask, write=write)))
        finally:
            source.close()
        return 0 if report["status"] == "PILOT_SUCCEEDED" else 1
    except Exception, KeyboardInterrupt:
        # May occur after send/mutation. Keep custody, never replay or infer NONE.
        report["status"] = "PILOT_RESULT_INCONCLUSIVE"
        return 1
    finally:
        report["duration_ms"] = max(0, int((time.monotonic() - started) * 1000))
        encoded = json.dumps(report, sort_keys=True, ensure_ascii=True)
        write(encoded)
        try:
            (retained / "pilot.json").write_text(encoded + "\n", encoding="utf-8")
        except OSError:
            write("PILOT_EVIDENCE_WRITE_FAILED; retain directory; do not replay")
            raise ValueError("PILOT_EVIDENCE_WRITE_FAILED") from None


def main(argv: Sequence[str] | None = None) -> int:
    options = list(sys.argv[1:] if argv is None else argv)
    if options not in ([], ["--plan"], ["--live"]):
        print("Invalid options; use --plan or --live; no credential flags")
        return 2
    print(json.dumps(plan(), sort_keys=True))
    if options != ["--live"]:
        return 0
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("PILOT_DECLINED; interactive terminal required")
        return 2
    try:
        if input("Type the exact displayed authorization: ") != AUTHORIZATION:
            print("PILOT_DECLINED")
            return 2
        return run_attended(input, print)
    except Exception, KeyboardInterrupt:
        print("PILOT_RESULT_INCONCLUSIVE; no raw error; no retry")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
