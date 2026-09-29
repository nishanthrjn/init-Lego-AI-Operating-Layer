"""ForgeAI command line: one reviewed task on one clean local repository.

Presentation and operator composition only. Task input is the objective and
targets; everything else is operator configuration from flags. The `replay`
binding is a deterministic offline ModelPort that returns recorded model
outputs in call order (Coding Agent, then reviewer); `ollama` uses LegoAI's
built-in local Ollama provider. Switching them changes configuration only.
"""

import argparse
import asyncio
import shutil
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

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
    ModelBindingConfig,
    ModelPurpose,
    OllamaSettings,
    TrustedModelContribution,
)
from legoai_engineering.coding.values import CodingTarget
from legoai_engineering.repository.mutation import FileChangeKind
from legoai_engineering.repository.workspace import RepositoryPath

from forgeai.composition import local_profile, run_task
from forgeai.domain import TaskDisposition, TaskRequest, TaskResult
from forgeai.guard import WorkspaceGuard

_MAX_LISTED = 20


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


def summarize(result: TaskResult) -> str:
    """Bounded human-readable summary; never file contents or tool output."""
    evidence = result.evidence
    lines = [f"disposition: {result.disposition.value}"]
    if result.failure is not None:
        lines.append(f"reason: {result.failure.value}")
    lines.append(f"run: {evidence.run_id}")
    if evidence.start is not None and evidence.start.head.commit is not None:
        lines.append(f"start HEAD: {evidence.start.head.commit.value[:12]}")
    if evidence.proposal is not None:
        lines.append(f"proposal: {evidence.proposal.summary[:200]}")
    if evidence.reworked:
        first = evidence.attempts[0]
        outcomes = ", ".join(
            f"{r.request.kind.value} {r.result.outcome.value if r.result else 'error'}"
            for r in first.checks
        )
        decision = first.review_decision
        lines.append("attempts: 2 (one rework after review #1 required changes)")
        lines.append(f"attempt 1 checks: {outcomes}")
        lines.append(f"attempt 1 review: {decision.value if decision else 'none'}")
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
    elif review is not None:
        lines.append(f"review: not completed ({review.status.value})")
    elif evidence.review_input_failure is not None:
        lines.append(f"review: not run ({evidence.review_input_failure.value})")
    return "\n".join(lines)


def _target(text: str) -> CodingTarget:
    path, _, kind = text.partition(":")
    operation = FileChangeKind.CREATE if kind == "create" else FileChangeKind.UPDATE
    if kind not in {"", "create", "update"}:
        raise argparse.ArgumentTypeError("target kind must be create or update")
    return CodingTarget(RepositoryPath(path), operation)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="forgeai", description="Run one bounded coding task (ForgeAI-1)."
    )
    parser.add_argument("repository", type=Path)
    parser.add_argument("--objective", required=True)
    parser.add_argument("--target", action="append", required=True, type=_target)
    parser.add_argument("--constraint", action="append", default=[])
    parser.add_argument("--binding", choices=("replay", "ollama"), default="replay")
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
    args = parser.parse_args(argv)
    if args.git is None or args.docker is None:
        parser.error("Git and Docker executables are required")
    if args.binding == "replay":
        if not args.replay:
            parser.error("--replay is required for the replay binding")
        outputs = [path.read_text(encoding="utf-8") for path in args.replay]
        binding = replay_binding(ReplayModel(*outputs))
    else:
        binding = ollama_binding(
            args.ollama_url, args.ollama_model, args.ollama_timeout
        )
    task = TaskRequest(args.objective, tuple(args.target), tuple(args.constraint))
    config = local_profile(
        args.repository.resolve(),
        tuple(target.path for target in task.targets),
        bindings=(binding,),
        binding=args.binding,
        git_executable=args.git.resolve(),
        docker_executable=args.docker.resolve(),
        now=datetime.now(UTC),
    )
    result = asyncio.run(run_task(config, task, WorkspaceGuard()))
    print(summarize(result))
    if result.disposition is TaskDisposition.SUCCEEDED:
        return 0
    return 2 if result.disposition is TaskDisposition.REJECTED else 1


if __name__ == "__main__":
    sys.exit(main())
