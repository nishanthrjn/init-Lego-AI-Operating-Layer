"""Explicit coding scope and M4 proposal data; no mutation authorization."""

from dataclasses import dataclass, field
from enum import Enum

from legoai.execution.agent.ports import AgentResult
from legoai.execution.agent.values import AgentExecutionStatus
from legoai.execution.values import ExecutionContext

from legoai_engineering.agent_output import OutputDiagnostic
from legoai_engineering.analyst.values import AcquisitionFailure, RepositoryEvidence
from legoai_engineering.coding.definition import coding_definition
from legoai_engineering.repository.mutation import (
    ContentDigest,
    FileChangeKind,
    RepositoryChangeSet,
    digest_text,
)
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import RepositoryPath


def _bytes(text: str, maximum: int, *, empty: bool = False) -> int:
    if type(text) is not str:
        raise TypeError("coding text requires str")
    if len(text) > maximum or (not empty and (not text or text.isspace())):
        raise ValueError("coding text is blank or oversized")
    try:
        size = len(text.encode("utf-8"))
    except UnicodeEncodeError:
        raise ValueError("coding text must be UTF-8") from None
    if size > maximum:
        raise ValueError("coding text exceeds byte limit")
    return size


def _strings(values: tuple[str, ...]) -> None:
    if type(values) is not tuple or len(values) > 8:
        raise ValueError("coding text collection requires at most eight items")
    for value in values:
        _bytes(value, 1024)


@dataclass(frozen=True, slots=True)
class CodingTarget:
    path: RepositoryPath
    operation: FileChangeKind

    def __post_init__(self) -> None:
        if (
            type(self.path) is not RepositoryPath
            or type(self.operation) is not FileChangeKind
        ):
            raise TypeError("coding target requires RepositoryPath and FileChangeKind")
        if self.operation not in {FileChangeKind.CREATE, FileChangeKind.UPDATE}:
            raise ValueError("coding supports create and update only")
        _bytes(self.path.value, 960)
        if any(part.startswith(".") for part in self.path.value.split("/")):
            raise ValueError("coding excludes hidden administrative path components")


def _targets(targets: tuple[CodingTarget, ...]) -> None:
    if type(targets) is not tuple or not 1 <= len(targets) <= 8:
        raise ValueError("coding requires one to eight targets")
    if any(type(target) is not CodingTarget for target in targets):
        raise TypeError("coding requires CodingTarget")
    paths = [target.path.value.casefold() for target in targets]
    if len(set(paths)) != len(paths) or any(
        other.startswith(path + "/")
        for path in paths
        for other in paths
        if path != other
    ):
        raise ValueError("duplicate, case alias or ancestor targets are unsupported")


# Read-only reference context: disclosed to the model, never editable scope.
MAX_REFERENCES = 8
MAX_REFERENCE_BYTES = 8192  # per file, the existing evidence file bound
MAX_REFERENCE_TOTAL_BYTES = 16384  # half of the Coding Agent input budget


def _references(
    references: tuple[RepositoryPath, ...], targets: tuple[CodingTarget, ...]
) -> None:
    if type(references) is not tuple or len(references) > MAX_REFERENCES:
        raise ValueError("coding allows at most eight reference paths")
    if any(type(path) is not RepositoryPath for path in references):
        raise TypeError("coding references require RepositoryPath")
    for path in references:
        _bytes(path.value, 960)
        if any(part.startswith(".") for part in path.value.split("/")):
            raise ValueError("coding excludes hidden administrative path components")
    keys = [path.value.casefold() for path in references]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate or case alias reference paths are unsupported")
    # A reference never doubles as a target: disclosure is not write scope.
    if set(keys) & {target.path.value.casefold() for target in targets}:
        raise ValueError("a reference path is also a target")


@dataclass(frozen=True, slots=True)
class CodingRequest:
    """`references` are read-only repository files disclosed to the model.

    They grant no mutation scope: only `targets` may appear in a proposal.
    """

    objective: str = field(repr=False)
    targets: tuple[CodingTarget, ...]
    constraints: tuple[str, ...] = field(repr=False)
    context: ExecutionContext
    references: tuple[RepositoryPath, ...] = ()

    def __post_init__(self) -> None:
        _bytes(self.objective, 2048)
        _targets(self.targets)
        _strings(self.constraints)
        if type(self.context) is not ExecutionContext:
            raise TypeError("coding requires ExecutionContext")
        _references(self.references, self.targets)


@dataclass(frozen=True, slots=True)
class CodingFile:
    """Observed current text; its digest is computed, never accepted from a caller."""

    target: CodingTarget
    current: RepositoryText | None = field(repr=False)
    digest: ContentDigest | None = field(init=False)

    def __post_init__(self) -> None:
        if type(self.target) is not CodingTarget:
            raise TypeError("coding file requires target")
        if self.target.operation is FileChangeKind.CREATE:
            if self.current is not None:
                raise ValueError("create requires observed absence")
            object.__setattr__(self, "digest", None)
        else:
            if type(self.current) is not RepositoryText:
                raise TypeError("update requires exact current RepositoryText")
            if self.current.path != self.target.path.value:
                raise ValueError("coding evidence path mismatch")
            _bytes(self.current.text, 8192, empty=True)
            object.__setattr__(self, "digest", digest_text(self.current.text))


@dataclass(frozen=True, slots=True)
class CodingEvidence:
    """Trusted bounded observations, not an atomic snapshot or current permission.

    `references` is read-only disclosed text, never a proposal precondition.
    """

    files: tuple[CodingFile, ...] = field(repr=False)
    references: RepositoryEvidence | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.files) is not tuple or not 1 <= len(self.files) <= 8:
            raise ValueError("coding evidence requires one to eight files")
        if any(type(file) is not CodingFile for file in self.files):
            raise TypeError("coding evidence requires CodingFile")
        _targets(tuple(file.target for file in self.files))
        paths = tuple(file.target.path.value for file in self.files)
        if paths != tuple(sorted(paths)):
            raise ValueError("coding evidence must be sorted by path")
        if (
            sum(
                len(file.current.text.encode("utf-8"))
                for file in self.files
                if file.current is not None
            )
            > 24576
        ):
            raise ValueError("coding evidence exceeds total byte limit")
        if self.references is not None:
            if type(self.references) is not RepositoryEvidence:
                raise TypeError("coding references require RepositoryEvidence")
            texts = self.references.files
            if len(texts) > MAX_REFERENCES or any(
                len(text.text.encode("utf-8")) > MAX_REFERENCE_BYTES for text in texts
            ):
                raise ValueError("coding reference exceeds its bound")
            if (
                sum(len(text.text.encode("utf-8")) for text in texts)
                > MAX_REFERENCE_TOTAL_BYTES
            ):
                raise ValueError("coding references exceed total byte limit")
            _references(
                tuple(RepositoryPath(text.path) for text in texts),
                tuple(file.target for file in self.files),
            )

    @property
    def reference_paths(self) -> tuple[RepositoryPath, ...]:
        if self.references is None:
            return ()
        return tuple(RepositoryPath(text.path) for text in self.references.files)


@dataclass(frozen=True, slots=True)
class CodingProposal:
    """Actual M4 values plus unverified narrative; never an apply request owner."""

    changeset: RepositoryChangeSet
    summary: str = field(repr=False)
    reasons: tuple[str, ...] = field(repr=False)
    risks: tuple[str, ...] = field(repr=False)
    unknowns: tuple[str, ...] = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.changeset) is not RepositoryChangeSet:
            raise TypeError("coding proposal requires RepositoryChangeSet")
        if not 1 <= len(self.changeset.changes) <= 8:
            raise ValueError("coding proposal requires one to eight changes")
        total = 0
        for change in self.changeset.changes:
            CodingTarget(change.path, change.kind)
            if change.text is None:
                raise ValueError("coding proposal requires replacement text")
            total += _bytes(change.text, 8192, empty=True)
        if total > 24576:
            raise ValueError("coding proposal exceeds total content byte limit")
        _bytes(self.summary, 2048)
        _strings(self.reasons)
        if len(self.reasons) != len(self.changeset.changes):
            raise ValueError("one reason is required per change")
        _strings(self.risks)
        _strings(self.unknowns)


class CodingStatus(Enum):
    SUCCEEDED = "succeeded"
    INVALID_REQUEST = "invalid_request"
    MODEL_FAILURE = "model_failure"
    OUTPUT_INVALID = "output_invalid"


@dataclass(frozen=True, slots=True)
class CodingResult:
    status: CodingStatus
    request: CodingRequest = field(repr=False)
    evidence: CodingEvidence | None = field(repr=False)
    agent_result: AgentResult | None
    proposal: CodingProposal | None
    acquisition_failure: AcquisitionFailure | None = None
    # Why output was rejected (OUTPUT_INVALID only); safe to display and keep.
    diagnostic: OutputDiagnostic | None = None

    def __post_init__(self) -> None:
        if (
            type(self.status) is not CodingStatus
            or type(self.request) is not CodingRequest
        ):
            raise TypeError("coding result requires status and request")
        if self.diagnostic is not None and (
            self.status is not CodingStatus.OUTPUT_INVALID
            or type(self.diagnostic) is not OutputDiagnostic
        ):
            raise ValueError("only rejected output carries an output diagnostic")
        if self.evidence is not None:
            if type(self.evidence) is not CodingEvidence:
                raise TypeError("coding result requires CodingEvidence")
            if {file.target for file in self.evidence.files} != set(
                self.request.targets
            ):
                raise ValueError(
                    "coding result evidence does not match requested scope"
                )
            if set(self.evidence.reference_paths) != set(self.request.references):
                raise ValueError(
                    "coding result references do not match requested references"
                )
        if self.status is CodingStatus.INVALID_REQUEST:
            if (
                type(self.acquisition_failure) is not AcquisitionFailure
                or self.agent_result is not None
                or self.proposal is not None
            ):
                raise ValueError(
                    "invalid request cannot carry an invocation or proposal"
                )
            return
        if self.acquisition_failure is not None or self.evidence is None:
            raise ValueError("coding invocation requires acquired evidence")
        agent = self.agent_result
        if type(agent) is not AgentResult:
            raise TypeError("coding result requires AgentResult")
        if (
            agent.definition != coding_definition()
            or agent.execution_id != self.request.context.execution_id
        ):
            raise ValueError("coding result Agent attribution mismatch")
        if self.status is CodingStatus.SUCCEEDED:
            if (
                agent.status is not AgentExecutionStatus.SUCCEEDED
                or type(self.proposal) is not CodingProposal
            ):
                raise ValueError("successful coding requires validated proposal")
            files = {file.target.path.value: file for file in self.evidence.files}
            for change in self.proposal.changeset.changes:
                file = files.get(change.path.value)
                if (
                    file is None
                    or change.kind is not file.target.operation
                    or change.expected != file.digest
                ):
                    raise ValueError("proposal scope or trusted precondition mismatch")
        else:
            if self.proposal is not None:
                raise ValueError("failed coding cannot return a partial proposal")
            allowed = (
                {AgentExecutionStatus.ROUTING_FAILED, AgentExecutionStatus.MODEL_FAILED}
                if self.status is CodingStatus.MODEL_FAILURE
                else {
                    AgentExecutionStatus.SUCCEEDED,
                    AgentExecutionStatus.OUTPUT_INVALID,
                }
            )
            if agent.status not in allowed:
                raise ValueError("coding status contradicts Agent outcome")
