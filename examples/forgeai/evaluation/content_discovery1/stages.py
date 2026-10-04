"""Evaluation-only staged confirmations; no write or worker invocation."""

import json
from dataclasses import dataclass

from legoai_engineering.analyst.api import RepositoryAnalyst
from legoai_engineering.analyst.authorized import (
    REPOSITORY_READ_ACTION,
    AuthorizedRepositoryEvidence,
)
from legoai_engineering.analyst.values import (
    RepositoryAnalysisRequest,
    RepositoryAnalysisResult,
    RepositoryAnalysisStatus,
)
from legoai_engineering.repository.errors import WorkspaceError, WorkspaceFailure
from legoai_engineering.repository.mutation import digest_text
from legoai_engineering.repository.structure import (
    RepositoryStructure,
    RepositoryStructurePolicy,
)
from legoai_engineering.repository.structure_authorized import (
    REPOSITORY_STRUCTURE_ACTION,
    AuthorizedRepositoryStructure,
)
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import (
    RepositoryPath,
    WorkspaceEntry,
    WorkspaceEntryKind,
)

from content_discovery1.data import Case
from content_discovery1.wiring import NOW, Replay, host_for
from legoai.kernel.references import ConfigurationRef
from legoai.runtime.api import GovernedHost, ModelPurpose


class Workspace:
    """Synthetic in-memory Port double, with bounded reads and observed I/O."""

    def __init__(self, files: tuple[RepositoryText, ...]) -> None:
        self.files = {f.path: f.text for f in files}
        self.reads: list[str] = []
        self.lists = 0

    def list_entries(
        self, directory: RepositoryPath | None
    ) -> tuple[WorkspaceEntry, ...]:
        assert directory is not None
        self.lists += 1
        prefix = directory.value + "/"
        entries: dict[str, WorkspaceEntryKind] = {}
        for path in self.files:
            if path.startswith(prefix):
                rest = path[len(prefix) :]
                entries[prefix + rest.split("/")[0]] = (
                    WorkspaceEntryKind.DIRECTORY
                    if "/" in rest
                    else WorkspaceEntryKind.FILE
                )
        if len(entries) > 512:
            raise WorkspaceError(WorkspaceFailure.LIMIT)
        return tuple(
            WorkspaceEntry(RepositoryPath(p), kind)
            for p, kind in sorted(entries.items())
        )

    def read_text(self, path: RepositoryPath) -> RepositoryText:
        if path.value not in self.files:
            raise WorkspaceError(WorkspaceFailure.MISSING)
        value = self.files[path.value]
        if len(value.encode()) > 8192:
            raise WorkspaceError(WorkspaceFailure.LIMIT)
        self.reads.append(path.value)
        return RepositoryText(path.value, value)


def files_in(structure: RepositoryStructure) -> frozenset[str]:
    return frozenset(
        e.path.value for e in structure.entries if e.kind is WorkspaceEntryKind.FILE
    )


def propose(structure: RepositoryStructure) -> tuple[str, ...]:
    return tuple(sorted(files_in(structure)))[:8]


@dataclass(frozen=True)
class ReadConfirmation:
    paths: tuple[str, ...]
    map_digest: str


def confirm_reads(
    exact: tuple[str, ...], preview: RepositoryStructure, allowed: tuple[str, ...]
) -> ReadConfirmation:
    if (
        len(exact) > 8
        or len(set(exact)) != len(exact)
        or not set(exact) <= files_in(preview) & set(allowed)
    ):
        raise ValueError("invalid confirmed read subset")
    return ReadConfirmation(tuple(sorted(exact)), preview.digest())


@dataclass
class Session:
    case: Case
    workspace: Workspace
    model: Replay
    host: GovernedHost
    reference: ConfigurationRef
    structure: AuthorizedRepositoryStructure

    def preview(self) -> RepositoryStructure:
        return self.structure.acquire(self.structure.security_context.tenant_context)

    def reader(self, confirmation: ReadConfirmation) -> AuthorizedRepositoryEvidence:
        return AuthorizedRepositoryEvidence(
            self.reference,
            self.workspace,
            self.host.security_context(
                self.reference, REPOSITORY_READ_ACTION, self.reference.instance
            ),
            self.host.authorization,
            tuple(RepositoryPath(p) for p in confirmation.paths),
            lambda: NOW,
        )


def session(
    case: Case, *, read_allowed: bool = True, output: str | None = None
) -> Session:
    if output is None:
        output = json.dumps(
            dict(
                status=case.replay_status,
                summary="Synthetic scripted claim; model quality unmeasured.",
                relevant_files=list(case.replay_relevant),
                findings=[],
                risks=[],
                unknowns=["Synthetic replay uncertainty."],
            )
        )
    model = Replay(output)
    host, ref = host_for(model, read_allowed=read_allowed)
    workspace = Workspace(case.files)
    structure = AuthorizedRepositoryStructure(
        ref,
        workspace,
        host.security_context(ref, REPOSITORY_STRUCTURE_ACTION, ref.instance),
        host.authorization,
        RepositoryStructurePolicy(tuple(RepositoryPath(p) for p in case.roots)),
        lambda: NOW,
    )
    return Session(case, workspace, model, host, ref, structure)


@dataclass(frozen=True)
class Observation:
    confirmation: ReadConfirmation
    result: RepositoryAnalysisResult | None
    candidates: tuple[str, ...]
    status: str


def interpret(
    result: RepositoryAnalysisResult, eligible: tuple[str, ...]
) -> tuple[str, tuple[str, ...]]:
    if (
        result.status is not RepositoryAnalysisStatus.SUCCEEDED
        or result.analysis is None
        or result.evidence is None
    ):
        return "insufficient_evidence", ()
    supplied = {f.path for f in result.evidence.files}
    candidates = tuple(
        sorted(
            p.value
            for p in result.analysis.relevant_files
            if p.value in supplied & set(eligible)
        )
    )
    return ("succeeded" if candidates else "insufficient_evidence"), candidates


async def analyze(
    s: Session,
    confirmation: ReadConfirmation,
    reader: AuthorizedRepositoryEvidence | None = None,
) -> Observation:
    current = s.preview()
    if current.digest() != confirmation.map_digest:
        raise ValueError("stale map confirmation")
    # Revalidate exact inputs, even if an evaluation caller constructs the value.
    confirm_reads(confirmation.paths, current, s.case.read_policy)
    if not confirmation.paths:
        return Observation(confirmation, None, (), "rejected_read_set")
    result = await RepositoryAnalyst(
        reader or s.reader(confirmation), s.host.agent_runtime()
    ).analyze(
        RepositoryAnalysisRequest(
            s.case.question,
            tuple(RepositoryPath(p) for p in confirmation.paths),
            s.host.model_execution(ModelPurpose.CHAT),
        )
    )
    status, candidates = interpret(result, s.case.edit_policy)
    return Observation(confirmation, result, candidates, status)


async def confirm_targets(
    s: Session, observation: Observation, exact: tuple[str, ...]
) -> tuple[str, ...]:
    """Return operator intent only. Never issue grants or invoke Coding/mutation."""
    current = s.preview()
    if current.digest() != observation.confirmation.map_digest:
        raise ValueError("stale final confirmation")
    if (
        len(exact) > 8
        or len(set(exact)) != len(exact)
        or not set(exact)
        <= files_in(current)
        & set(s.case.edit_policy)
        & set(observation.confirmation.paths)
    ):
        raise ValueError("invalid confirmed target subset")
    if observation.result is None or observation.result.evidence is None:
        if exact:
            raise ValueError("no evidence for target confirmation")
        return ()
    previous = observation.result.evidence
    fresh = await s.reader(observation.confirmation).acquire(
        tuple(RepositoryPath(p) for p in observation.confirmation.paths),
        s.structure.security_context.tenant_context,
    )
    if tuple((f.path, digest_text(f.text)) for f in previous.files) != tuple(
        (f.path, digest_text(f.text)) for f in fresh.files
    ):
        raise ValueError("stale content evidence")
    return tuple(sorted(exact))
