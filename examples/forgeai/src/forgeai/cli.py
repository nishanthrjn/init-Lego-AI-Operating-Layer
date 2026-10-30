"""ForgeAI command line: one supervised, reviewed task on one clean local repository.

Presentation and operator composition only. Task input is the task text and
the operator-approved targets; everything else is operator configuration from
flags. The `replay` binding is a deterministic offline ModelPort that returns
recorded model outputs in call order (Coding Agent, then reviewer); `ollama`
uses LegoAI's built-in local Ollama provider. Switching them changes
configuration only.

Every validated proposal is shown and needs an explicit interactive "y" before
anything is written. The default answer is No; EOF, Ctrl+C and a
non-interactive terminal all decline, and there is no automatic approval.

    forgeai run --repo PATH --task TEXT --target PATH[:create] [--target ...]
                [--context PATH ...]

`--context` files are disclosed read-only to the Coding Agent; they are never
editable and a proposal that touches one is rejected.

The pre-v0.1 form `forgeai PATH --objective TEXT --target ...` still works,
with the same approval step.
"""

import argparse
import asyncio
import difflib
import hashlib
import json
import shutil
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Never

from legoai.intelligence.model.ports import ModelPort
from legoai.intelligence.model.routing import ModelRequirement
from legoai.intelligence.model.values import (
    ChatRequest,
    ChatResult,
    EmbeddingRequest,
    EmbeddingResult,
    ModelId,
    ProviderId,
)
from legoai.plugins.values import PluginId
from legoai.runtime.api import (
    HostError,
    ModelBindingConfig,
    ModelPurpose,
    OllamaSettings,
    RemoteModelRuntime,
    TrustedModelContribution,
)
from legoai_engineering.analyst.values import AcquisitionFailure
from legoai_engineering.coding.values import CodingTarget
from legoai_engineering.repository.errors import WorkspaceError
from legoai_engineering.repository.mutation import FileChangeKind
from legoai_engineering.repository.workspace import RepositoryPath
from legoai_engineering.reviewer.values import FindingSeverity
from legoai_engineering.sandbox.errors import SandboxFailure

from forgeai.composition import (
    ForgeAIConfig,
    bind_remote,
    discover_guidance,
    local_profile,
    prepare_run,
    remote_credentials,
    sandbox_readiness,
)
from forgeai.domain import (
    CheckProfile,
    OperatorDecision,
    ProposalReview,
    ReworkTrigger,
    RunStage,
    TaskDisposition,
    TaskFailure,
    TaskRequest,
    TaskResult,
)
from forgeai.guard import WorkspaceGuard
from forgeai.guidance import GuidanceRefusal, guidance_candidates, guidance_summary
from forgeai.line_endings import is_consistent_crlf
from forgeai.remote import BINDING, RemoteProfile, load_profile
from forgeai.report import ModelBindingKind, encode_report, run_report
from forgeai.repository_context import ContextPreflight, context_summary

_MAX_LISTED = 20
_PATCH_LINES = 800  # the whole patch is shown or approval is refused
_PATCH_BYTES = 98_304
_BIDI = frozenset(
    "\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"
)
_STEPS = 7
type Ask = Callable[[str], str]
type Out = Callable[[str], None]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        # Unknown options are never a credential input channel, even on refusal.
        if message.startswith("unrecognized arguments:"):
            message = (
                "unrecognized arguments; see --help (no credential flags supported)"
            )
        super().error(message)


class ReplayModel:
    """Deterministic offline ModelPort: call N returns recorded output N.

    An Exception in the sequence is raised instead (a provider failure). A
    call beyond the recorded outputs fails loudly; nothing is ever reused.
    """

    def __init__(self, *outputs: str | Exception) -> None:
        if not outputs:
            raise ValueError("replay requires at least one recorded output")
        self.outputs = outputs
        self.calls = 0

    async def chat(self, request: ChatRequest) -> ChatResult:
        index = self.calls
        self.calls += 1
        if index >= len(self.outputs):
            raise RuntimeError("replay model received an unrecorded call")
        output = self.outputs[index]
        if isinstance(output, Exception):
            raise output
        return ChatResult(output, ModelId("replay"), ProviderId("forgeai-replay"), None)

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        raise NotImplementedError("the replay model supports chat only")


def replay_binding(model: ModelPort) -> ModelBindingConfig:
    return ModelBindingConfig(
        "replay",
        ModelRequirement("engineering-reasoning"),
        TrustedModelContribution(
            PluginId("forgeai", "replay"),
            ProviderId("forgeai-replay"),
            ModelId("replay"),
            frozenset({ModelPurpose.CHAT}),
            lambda: model,
        ),
    )


def ollama_binding(url: str, model: str, timeout: float) -> ModelBindingConfig:
    return ModelBindingConfig(
        "ollama",
        ModelRequirement("engineering-reasoning"),
        OllamaSettings(url, model, model, timeout, ProviderId("ollama")),
    )


def ollama_ready(url: str, model: str, timeout: float = 5.0) -> str | None:
    """Startup check: None when the model is installed, else why not.

    Reads the local model list only (`GET /api/tags`); no inference.
    """
    try:
        with urllib.request.urlopen(
            url.rstrip("/") + "/api/tags", timeout=timeout
        ) as r:
            body = json.loads(r.read(1_048_577))
    except urllib.error.URLError, OSError, ValueError:
        return f"Ollama is not reachable at {url}; start it with `ollama serve`"
    names = {m.get("name") for m in body.get("models", []) if isinstance(m, dict)}
    if model not in names:
        return f"model {model} is not installed; run `ollama pull {model}`"
    return None


def readiness_message(failure: SandboxFailure) -> str:
    """One readable startup failure with one next action; no traceback."""
    if failure is SandboxFailure.RUNTIME_UNAVAILABLE:
        return (
            "Docker is not ready: the Docker CLI or the Docker Desktop Linux engine "
            "is unavailable. Start Docker Desktop (Linux containers) and retry."
        )
    if failure is SandboxFailure.ENVIRONMENT_UNAVAILABLE:
        return (
            "Docker is running, but the qualified ForgeAI checks image is not "
            "present locally. Build it from sandbox-images/python-checks (CR-2a) "
            "and retry; ForgeAI never pulls or builds images."
        )
    if failure is SandboxFailure.UNSUPPORTED:
        return (
            "Docker is running without the sandbox controls ForgeAI requires "
            "(Windows host, Linux engine, cgroup v2, seccomp, resource limits). "
            "Use Docker Desktop's Linux engine and retry."
        )
    return (
        f"Docker readiness could not be confirmed ({failure.value}). "
        "Check Docker Desktop and retry."
    )


def _kind(value: FileChangeKind) -> str:
    return "create" if value is FileChangeKind.CREATE else "update"


def header(config: ForgeAIConfig, task: TaskRequest, model: str) -> str:
    """Scope shown before any model call or effect."""
    lines = [
        "ForgeAI v0.1: supervised local engineering task",
        f"repository: {config.repository}",
        f"task: {task.objective[:400]}",
        "editable targets (operator-selected; the model cannot add any):",
        *(f"  - {t.path.value} ({_kind(t.operation)})" for t in task.targets),
    ]
    if task.context:
        lines.append(
            "read-only model context (disclosed to the Coding Agent; NOT editable):"
        )
        lines += [f"  - {path.value} (read-only)" for path in task.context]
    else:
        lines.append("read-only model context: none")
    lines += [f"constraint: {c[:200]}" for c in task.constraints]
    checks = ", ".join(c.kind.value for c in config.check_plan)
    image = (
        config.sandbox_image.value
        if config.check_profile is CheckProfile.GENERIC
        else "prepared project environment"
    )
    lines.append(f"checks: {checks} (sandboxed, image {image})")
    lines.append(f"model: {model}")
    lines.append("Nothing is written until you approve the proposal.")
    return "\n".join(lines)


def safe(text: str) -> str:
    """Terminal-safe rendering: control and bidi characters become visible escapes.

    Proposed content is model output; it must not move the cursor, recolor,
    overwrite or reorder what the operator sees.
    """
    return "".join(
        char
        if char == "\t" or (char.isprintable() and char not in _BIDI)
        else f"\\u{ord(char):04x}"
        for char in text
    )


def _lines(text: str) -> list[str]:
    """Split on LF only, keeping each LF: CR, form feed and Unicode separators
    stay visible data, and a missing final newline is a visible difference."""
    parts = text.split(chr(10))
    return [part + chr(10) for part in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def patch(review: ProposalReview) -> list[str]:
    """Unified diff of the exact proposal against its digest-bound current text.

    A file whose proposed content equals its current content yields no lines
    (the listing marks it unchanged). The missing-final-newline marker follows
    exactly the diff line that lacks one, on either side, never anywhere else.
    """
    lines: list[str] = []
    for change, before in zip(
        review.proposal.changeset.changes, review.before, strict=True
    ):
        path = change.path.value
        crlf = is_consistent_crlf(before) and is_consistent_crlf(change.text)
        diff = difflib.unified_diff(
            _lines(before or ""),
            _lines(change.text or ""),
            "/dev/null" if before is None else f"a/{path}",
            f"b/{path}",
        )
        for index, line in enumerate(diff):
            if index < 2 or line.startswith("@@"):  # file headers and hunk ranges
                lines.append(safe(line.removesuffix(chr(10))))
                if index == 1 and crlf:
                    lines.append(
                        "line endings: CRLF (both versions; not shown per line)"
                    )
            elif line.endswith(chr(10)):
                displayed = line[:-1]
                lines.append(safe(displayed.removesuffix("\r") if crlf else displayed))
            else:
                lines.append(safe(line))
                lines.append("\\ No newline at end of file")
    return lines


def unchanged(change_text: str | None, before: str | None) -> bool:
    return before is not None and before == (change_text or "")


def fingerprint(review: ProposalReview) -> str:
    """Short display id of the exact proposal identity the decision binds to."""
    encoded = json.dumps(review.identity, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:12]


def preview(review: ProposalReview) -> str:
    """The proposal and its full unified diff, or an explicit bound refusal."""
    proposal = review.proposal
    kind = "Rework proposal" if review.rework is not None else "Proposal"
    lines = [
        f"{kind} (attempt {review.attempt}, id {fingerprint(review)}): "
        f"{safe(proposal.summary[:400])}"
    ]
    if review.rework is not None:
        lines.append(f"  reason for rework: {review.rework.value}")
        lines.append("  feedback given to the Coding Agent (bounded, as data):")
        lines += [
            f"    | {safe(line)}"
            for item in review.feedback
            for line in item.split("\n")
        ]
    for change, reason, before in zip(
        proposal.changeset.changes, proposal.reasons, review.before, strict=True
    ):
        text = change.text or ""
        size = f"{len(text.splitlines())} lines, {len(text.encode('utf-8'))} bytes"
        if unchanged(change.text, before):
            size += "; unchanged, content identical to the current file"
        lines.append(f"  {_kind(change.kind)} {change.path.value} ({size})")
        lines.append(f"    why: {safe(reason[:300])}")
    lines += [f"  risk: {safe(risk[:300])}" for risk in proposal.risks]
    lines += [f"  unknown: {safe(item[:300])}" for item in proposal.unknowns]
    diff = patch(review)
    if fits(diff):
        lines.append("--- proposed patch (exactly what will be written) ---")
        lines += diff
        lines.append("--- end of patch ---")
    else:
        lines.append(
            f"PREVIEW EXCEEDS DISPLAY BOUND: {len(diff)} diff lines "
            f"(limit {_PATCH_LINES} lines, {_PATCH_BYTES} bytes); the full change "
            "cannot be shown, so it cannot be approved here."
        )
    return "\n".join(lines)


def fits(diff: list[str]) -> bool:
    return (
        len(diff) <= _PATCH_LINES
        and sum(len(line.encode("utf-8")) + 1 for line in diff) <= _PATCH_BYTES
    )


def terminal_context_confirmer(
    ask: Ask | None, out: Out
) -> Callable[[ContextPreflight], bool]:
    def confirm(inventory: ContextPreflight) -> bool:
        out(context_summary(inventory))
        out("Context confirmation is not disclosure or mutation approval.")
        if ask is None:
            return False
        try:
            answer = ask("Confirm this required repository context? [y/N] ")
            return answer.strip().lower() in {"y", "yes"}
        except EOFError, KeyboardInterrupt:
            return False

    return confirm


def terminal_approver(
    ask: Ask | None, out: Out
) -> Callable[[ProposalReview], OperatorDecision]:
    """Explicit operator decision; anything but y/yes declines."""

    def approve(review: ProposalReview) -> OperatorDecision:
        out(preview(review))
        if not fits(patch(review)):
            out("Not approved: a change you cannot fully see is never applied.")
            return OperatorDecision.decline(review)
        if ask is None:
            out("Not approved: no interactive terminal (approval is never automatic).")
            return OperatorDecision.decline(review)
        try:
            answer = ask(
                "Apply this rework proposal? [y/N] "
                if review.rework is not None
                else "Apply this proposal? [y/N] "
            )
        except EOFError, KeyboardInterrupt:
            out("\nNot approved.")
            return OperatorDecision.decline(review)
        if answer.strip().lower() in {"y", "yes"}:
            return OperatorDecision.approve(review)
        out("Not approved.")
        return OperatorDecision.decline(review)

    return approve


def reporter(out: Out) -> Callable[[RunStage, int], None]:
    steps = {
        RunStage.REPOSITORY_VERIFIED: 1,
        RunStage.PROPOSAL_GENERATED: 2,
        RunStage.AWAITING_APPROVAL: 3,
        RunStage.CHANGES_APPLIED: 4,
        RunStage.CHECKS_COMPLETED: 5,
        RunStage.REVIEW_COMPLETED: 6,
    }

    def progress(stage: RunStage, attempt: int) -> None:
        if stage is RunStage.REWORK_STARTED:
            out("[rework] review #1 requested changes; one bounded rework (attempt 2)")
            return
        if stage is RunStage.CHECK_REWORK_STARTED:
            out(
                "[rework] checks reported code findings; one bounded rework "
                "(attempt 2) using that check output"
            )
            return
        suffix = " (attempt 2)" if attempt == 2 else ""
        out(f"[{steps[stage]}/{_STEPS}] {stage.value.capitalize()}{suffix}")

    return progress


def summarize(result: TaskResult, repository: Path | None = None) -> str:
    """Bounded human-readable summary; never file contents or tool output."""
    evidence = result.evidence
    lines = [f"disposition: {result.disposition.value}"]
    if result.failure is not None:
        lines.append(f"reason: {result.failure.value}")
    if evidence.context_preflight is not None:
        lines.append(context_summary(evidence.context_preflight))
        lines.append(f"context confirmed: {evidence.context_confirmed}")
    for confirmation in evidence.context_confirmations:
        outcome = "CONTEXT_CONFIRMED"
        if confirmation.reason is not None:
            outcome = confirmation.reason.value
        lines.append(
            f"context confirmation requested: {confirmation.binding.identity.value}; "
            f"inventory: {confirmation.binding.inventory.value}; result: {outcome}"
        )
    if evidence.preparation_failure is not None:
        lines.append("environment preparation: " + evidence.preparation_failure.value)
    if evidence.preparation_infrastructure_failure is not None:
        lines.append(
            "environment infrastructure: "
            + evidence.preparation_infrastructure_failure.value
        )
    lines.append(f"run: {evidence.run_id}")
    if evidence.start is not None and evidence.start.head.commit is not None:
        lines.append(f"start HEAD: {evidence.start.head.commit.value[:12]}")
    lines.append(f"attempt count: {len(evidence.attempts)}")
    if evidence.proposal is not None:
        lines.append(f"proposal: {evidence.proposal.summary[:200]}")
    if result.failure is TaskFailure.PROPOSAL_NO_CHANGE:
        lines.append("proposal claim: unverified; this attempt changes no file")
    if evidence.reworked:
        first = evidence.attempts[0]
        outcomes = ", ".join(
            f"{r.request.kind.value} {r.result.outcome.value if r.result else 'error'}"
            for r in first.checks
        )
        decision = first.review_decision
        lines.append(
            "attempts: 2 (one rework after non-discriminating tests)"
            if evidence.rework_trigger is ReworkTrigger.TEST_STRENGTH
            else "attempts: 2 (one rework after attempt 1 checks reported findings)"
            if evidence.rework_trigger is ReworkTrigger.CHECK_FINDINGS
            else "attempts: 2 (one rework after review #1 required changes)"
        )
        lines.append(f"attempt 1 checks: {outcomes}")
        lines.append(f"attempt 1 review: {decision.value if decision else 'not run'}")
    if result.failure is TaskFailure.PROPOSAL_DECLINED:
        lines.append("approval: declined; no file was written, checked or reviewed")
    acquisition = (
        evidence.attempts[-1].acquisition_failure if evidence.attempts else None
    )
    if acquisition is not None:
        lines.append(f"evidence: {evidence_message(acquisition)}")
        lines.append("the Coding Agent model was not called for this attempt")
    diagnostics = (
        ("coding output invalid:", evidence.latest.coding_diagnostic),
        (
            "review output invalid:",
            evidence.review.diagnostic if evidence.review is not None else None,
        ),
    )
    for title, diagnostic in diagnostics:
        if diagnostic is not None:
            lines.append(title)
            lines.append(
                f"  reason: {diagnostic.rejection.name} ({diagnostic.rejection.value})"
            )
            lines.append(f"  field: {diagnostic.location or '(whole reply)'}")
            lines.append("  no retry or repair was attempted; raw output is not shown")
    changed = [path.value for path in evidence.changed_paths]
    lines.append(f"changed files: {', '.join(changed[:_MAX_LISTED]) or 'none'}")
    for record in evidence.checks:
        if record.result is not None:
            status = record.result.outcome.value
        elif record.error is not None:
            status = f"error ({record.error.name.lower()})"
        else:
            status = "error (invalid check target)"
        lines.append(f"check {record.request.kind.value}: {status}")
    for request in evidence.planned_checks[len(evidence.checks) :]:
        if evidence.applied is not None:
            lines.append(f"check {request.kind.value}: not run")
    if evidence.final is not None:
        head = (
            "unchanged"
            if evidence.start is not None and evidence.final.head == evidence.start.head
            else "CHANGED"
        )
        paths = [entry.path.value for entry in evidence.final.entries]
        lines.append(f"final HEAD: {head}; working-tree changes: {len(paths)}")
    elif evidence.final_failure is not None:
        lines.append("final Git state: unavailable")
    review = evidence.review
    if review is not None and review.review is not None:
        lines.append(f"review: {review.review.decision.value}")
        lines.append(f"review summary: {review.review.summary[:200]}")
        for finding in review.review.findings:
            lines.append(
                f"review finding ({finding.severity.value}, "
                f"{finding.category.value}): {finding.message[:200]}"
            )
        blocking = sum(
            f.severity is FindingSeverity.BLOCKING for f in review.review.findings
        )
        lines.append(f"blocking findings: {blocking}")
    elif review is not None:
        lines.append(f"review: not completed ({review.status.value})")
    elif evidence.review_input_failure is not None:
        lines.append(f"review: not run ({evidence.review_input_failure.value})")
    if evidence.proposal is not None:
        lines += [f"risk: {risk[:200]}" for risk in evidence.proposal.risks]
        lines += [f"unknown: {item[:200]}" for item in evidence.proposal.unknowns]
    if changed and result.disposition is not TaskDisposition.SUCCEEDED:
        lines.append(
            "WARNING: changes remain in the working tree (nothing was rolled back): "
            + ", ".join(changed[:_MAX_LISTED])
        )
    if changed and repository is not None:
        lines.append(f"inspect: git -C {repository} diff -- {' '.join(changed)}")
    return "\n".join(lines)


def evidence_message(failure: AcquisitionFailure) -> str:
    """Why target or read-only context evidence could not be disclosed."""
    if failure is AcquisitionFailure.DENIED:
        return (
            "disclosure was not authorized for an editable target or read-only "
            "context path (denied)"
        )
    if failure is AcquisitionFailure.BOUNDARY:
        return (
            "a target or read-only context path is outside the repository "
            "workspace (boundary)"
        )
    if failure is AcquisitionFailure.BUDGET:
        return (
            "a target or read-only context file exceeds a size bound: 8192 bytes "
            "per context file, 16384 bytes of context in total, 32768 bytes of "
            "Coding Agent input (budget)"
        )
    return (
        "an editable target or read-only context file could not be read: "
        "missing, not a regular file, excluded by the workspace policy, or a "
        f"create target that already exists ({failure.value})"
    )


def _context(text: str) -> RepositoryPath:
    try:
        return RepositoryPath(text)
    except TypeError, ValueError, WorkspaceError:
        raise argparse.ArgumentTypeError(
            f"invalid read-only context {text!r}: use a relative file path "
            "inside the repository"
        ) from None


def _target(text: str) -> CodingTarget:
    path, _, kind = text.partition(":")
    operation = FileChangeKind.CREATE if kind == "create" else FileChangeKind.UPDATE
    if kind not in {"", "create", "update"}:
        raise argparse.ArgumentTypeError("target kind must be create or update")
    try:
        return CodingTarget(RepositoryPath(path), operation)
    except TypeError, ValueError, WorkspaceError:
        raise argparse.ArgumentTypeError(
            f"invalid target {path!r}: use a relative path inside the repository"
        ) from None


def _common(parser: argparse.ArgumentParser, binding: str) -> None:
    parser.add_argument(
        "--discover-guidance",
        action="store_true",
        help="discover bounded repository guidance as read-only context to confirm",
    )
    parser.add_argument(
        "--json-report",
        action="store_true",
        help="also print one bounded machine-readable result line (schema forgeai-run-report/1); no file is written",
    )
    parser.add_argument(
        "--check-profile",
        choices=("generic", "project"),
        default="generic",
        help="generic: fixed checks image; project: locked Python dependencies, explicit network preparation and offline checks",
    )
    parser.add_argument(
        "--target",
        action="append",
        required=True,
        type=_target,
        help="editable path, optionally PATH:create (repeat; 1-8)",
    )
    parser.add_argument(
        "--context",
        action="append",
        default=[],
        type=_context,
        help=(
            "existing file disclosed read-only to the Coding Agent, never "
            "editable (repeat; 0-8)"
        ),
    )
    parser.add_argument("--constraint", action="append", default=[])
    parser.add_argument("--test-strength", action="store_true", default=False)
    parser.add_argument(
        "--binding", choices=("replay", "ollama", BINDING), default=binding
    )
    parser.add_argument(
        "--remote-profile", type=Path, help="bounded non-secret operator policy TOML"
    )
    parser.add_argument(
        "--remote-custody",
        type=Path,
        help="existing owner-local custody directory outside the repository",
    )
    parser.add_argument(
        "--replay",
        type=Path,
        action="append",
        default=[],
        help=(
            "recorded model outputs in call order: coding, review; after a "
            "CHANGES_REQUIRED review, also the rework coding and final review"
        ),
    )
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--ollama-model", default="qwen2.5-coder:7b")
    parser.add_argument("--ollama-timeout", type=float, default=300.0)
    parser.add_argument("--git", type=Path, default=shutil.which("git"))
    parser.add_argument("--docker", type=Path, default=shutil.which("docker"))


def _parse(argv: Sequence[str]) -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    if argv and argv[0] == "run":
        parser = SafeArgumentParser(
            prog="forgeai run",
            description="Run one supervised coding task (ForgeAI v0.1).",
        )
        parser.add_argument("--repo", type=Path, required=True)
        parser.add_argument("--task", required=True)
        _common(parser, "ollama")
        args = parser.parse_args(argv[1:])
        return parser, args
    parser = SafeArgumentParser(
        prog="forgeai",
        description="Run one bounded coding task (pre-v0.1 syntax; see `forgeai run`).",
    )
    parser.add_argument("repo", type=Path)
    parser.add_argument("--objective", dest="task", required=True)
    _common(parser, "replay")
    return parser, parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    *,
    ask: Ask | None = input,
    out: Out = print,
    ready: Callable[[ForgeAIConfig], SandboxFailure | None] = sandbox_readiness,
) -> int:
    """The answer is read from stdin; only an explicit y/yes approves.

    An empty or closed stdin (EOF) declines, so unattended runs never approve.
    `ask=None` means no operator can answer: every proposal is declined.
    """
    parser, args = _parse(list(sys.argv[1:] if argv is None else argv))
    if args.discover_guidance and args.binding == BINDING:
        parser.error("--discover-guidance is not yet supported with the remote binding")
    kind = {
        "replay": ModelBindingKind.REPLAY,
        "ollama": ModelBindingKind.OLLAMA,
        BINDING: ModelBindingKind.OPENAI_COMPATIBLE_REMOTE,
    }[args.binding]
    repository: Path = args.repo
    if not repository.is_dir():
        parser.error(f"repository not found: {repository}")
    if not (repository / ".git").exists():
        parser.error(f"not a Git repository (no .git): {repository}")
    if args.git is None or args.docker is None:
        parser.error("Git and Docker executables are required")
    remote: RemoteProfile | None = None
    if args.binding != BINDING and (args.remote_profile or args.remote_custody):
        parser.error("remote options require the explicit remote binding")
    if args.binding == "replay":
        if not args.replay:
            parser.error("--replay is required for the replay binding")
        outputs = [path.read_text(encoding="utf-8") for path in args.replay]
        binding = replay_binding(ReplayModel(*outputs))
        model = "replay (recorded outputs; not a live model)"
    elif args.binding == BINDING:
        if args.remote_profile is None or args.remote_custody is None:
            parser.error(
                "remote binding requires --remote-profile and --remote-custody"
            )
        try:
            remote = load_profile(args.remote_profile)
            remote.validate(datetime.now(UTC))
            binding = remote.binding()
        except OSError, TypeError, ValueError:
            out(
                "startup refused: invalid, expired or unsupported non-secret remote profile"
            )
            return 2
        model = f"remote {remote.provider.value}/{remote.model}"
    else:
        problem = ollama_ready(args.ollama_url, args.ollama_model)
        if problem is not None:
            parser.error(problem)
        binding = ollama_binding(
            args.ollama_url, args.ollama_model, args.ollama_timeout
        )
        model = f"ollama {args.ollama_model} at {args.ollama_url}"
    try:
        task = TaskRequest(
            args.task,
            tuple(args.target),
            tuple(args.constraint),
            tuple(args.context),
        )
    except (TypeError, ValueError) as error:
        parser.error(f"invalid task: {error}")
    root = repository.resolve()
    uv_executable = shutil.which("uv")
    try:
        config = local_profile(
            root,
            # Editable scope comes from targets only; context never joins it.
            tuple(target.path for target in task.targets),
            context_paths=task.context,
            bindings=(binding,),
            binding=args.binding,
            git_executable=args.git.resolve(),
            docker_executable=args.docker.resolve(),
            now=datetime.now(UTC),
            check_profile=CheckProfile(args.check_profile),
            test_strength=args.test_strength,
            uv_executable=Path(uv_executable) if uv_executable else None,
        )
    except (TypeError, ValueError) as error:
        parser.error(f"invalid configuration: {error}")
    if args.discover_guidance:
        try:
            inventory = asyncio.run(
                discover_guidance(config, guidance_candidates(task))
            )
        except Exception:
            inventory = GuidanceRefusal.UNEXPECTED_ERROR
        if isinstance(inventory, GuidanceRefusal):
            out(
                "startup refused: guidance discovery "
                + inventory.value
                + "; no model was called and nothing was written"
            )
            return 2
        out(guidance_summary(inventory))
        try:
            task = TaskRequest(
                task.objective,
                task.targets,
                task.constraints,
                task.context + inventory.included_paths,
            )
            merged = local_profile(
                root,
                config.editable_paths,
                context_paths=task.context,
                bindings=(binding,),
                binding=args.binding,
                git_executable=config.git_executable,
                docker_executable=config.docker_executable,
                now=datetime.now(UTC),
                check_profile=config.check_profile,
                test_strength=config.test_strength,
                uv_executable=config.uv_executable,
            )
            # Retain the exact operator authority and expiry across the rebuild.
            config = replace(merged, host=config.host)
        except Exception:
            out(
                "startup refused: guidance discovery UNEXPECTED_ERROR; "
                "no model was called and nothing was written"
            )
            return 2
    if remote is not None:
        source = remote_credentials(config)
        try:
            try:
                config = bind_remote(
                    config,
                    remote,
                    task,
                    RemoteModelRuntime(
                        source, args.remote_custody.resolve(), timedelta(minutes=5)
                    ),
                    now=datetime.now(UTC),
                )
            except (
                HostError,
                OSError,
                TypeError,
                ValueError,
                RuntimeError,
                EOFError,
                KeyboardInterrupt,
            ):
                # Never interpolate exceptions from credential provisioning/runtime.
                out("startup refused: remote credential, policy or custody unavailable")
                return 2
            return _execute(
                config,
                task,
                model,
                ask=ask,
                out=out,
                ready=ready,
                kind=kind,
                json_report=args.json_report,
            )
        finally:
            source.close()
    return _execute(
        config,
        task,
        model,
        ask=ask,
        out=out,
        ready=ready,
        kind=kind,
        json_report=args.json_report,
    )


def _execute(
    config: ForgeAIConfig,
    task: TaskRequest,
    model: str,
    *,
    ask: Ask | None,
    out: Out,
    ready: Callable[[ForgeAIConfig], SandboxFailure | None],
    kind: ModelBindingKind = ModelBindingKind.REPLAY,
    json_report: bool = False,
) -> int:
    root = config.repository
    # Before any model call or effect: refuse unless the checks sandbox is ready.
    # PROJECT owns readiness inside its guarded preflight, after repository and
    # metadata validation. GENERIC retains its existing startup probe.
    failure = ready(config) if config.check_profile is CheckProfile.GENERIC else None
    if failure is not None:
        out("startup refused: " + readiness_message(failure))
        out("no model was called and nothing was written")
        return 2
    if config.check_profile is CheckProfile.GENERIC:
        out(header(config, task, model))

    def preflight(message: str) -> None:
        out(message)
        if message == "checks: Ruff, mypy, pytest; check network: disabled":
            out(header(config, task, model))

    try:
        # Host and adapter composition only; no model call or effect yet.
        prepared = prepare_run(
            config,
            WorkspaceGuard(),
            approve=terminal_approver(ask, out),
            progress=reporter(out),
            preflight=preflight,
            confirm_disclosure=remote_confirmer(ask, out),
            confirm_context=terminal_context_confirmer(ask, out),
        )
    except HostError as error:
        out(f"configuration error: {error.failure.value}")
        return 1
    except (OSError, TypeError, ValueError) as error:
        out(
            "configuration error: invalid remote configuration"
            if config.remote_profile
            else f"configuration error: {error}"
        )
        return 1
    result = asyncio.run(prepared.worker.run(task, prepared.context))
    out(f"[{_STEPS}/{_STEPS}] Final result")
    out(summarize(result, root))
    if json_report:
        try:
            encoded = encode_report(run_report(result, kind))
        except ValueError:
            out("forgeai-report: REPORT_UNAVAILABLE (bound exceeded)")
        else:
            out("forgeai-report: " + encoded)
    if result.disposition is TaskDisposition.SUCCEEDED:
        return 0
    return 2 if result.disposition is TaskDisposition.REJECTED else 1


def remote_confirmer(ask: Ask | None, out: Out) -> Callable[[str], bool]:
    def confirm(preview_text: str) -> bool:
        out("\n".join(safe(line) for line in preview_text.split("\n")))
        if ask is None or (ask is input and not sys.stdin.isatty()):
            return False
        try:
            return ask(
                "Send the listed data to this provider/model? [y/N] "
            ).strip().lower() in {"y", "yes"}
        except EOFError, KeyboardInterrupt:
            return False

    return confirm


if __name__ == "__main__":
    sys.exit(main())
