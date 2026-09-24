"""Bounded analysis data. Source content and model claims are never authority."""

from dataclasses import dataclass, field
from enum import Enum

from legoai.execution.agent.ports import AgentResult
from legoai.execution.agent.values import AgentExecutionStatus
from legoai.execution.values import ExecutionContext

from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import RepositoryPath


def _text(value: str, limit: int) -> None:
    if type(value) is not str:
        raise TypeError("analysis text requires str")
    if not value or len(value) > limit or value.isspace():
        raise ValueError("analysis text is blank or oversized")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError:
        raise ValueError("analysis text is not UTF-8") from None
    if size > limit:
        raise ValueError("analysis text is oversized")


def _paths(paths: tuple[RepositoryPath, ...], *, empty: bool = False) -> None:
    if type(paths) is not tuple:
        raise TypeError("analysis paths require a tuple of RepositoryPath")
    if not (0 if empty else 1) <= len(paths) <= 8:
        raise ValueError("analysis requires at most eight paths")
    if any(type(p) is not RepositoryPath for p in paths):
        raise TypeError("analysis paths require RepositoryPath")
    if len({p.value.casefold() for p in paths}) != len(paths):
        raise ValueError("duplicate analysis paths")
    try:
        for path in paths:
            path.value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("analysis paths must be UTF-8") from None


@dataclass(frozen=True, slots=True)
class RepositoryAnalysisRequest:
    question: str = field(repr=False)
    targets: tuple[RepositoryPath, ...]
    context: ExecutionContext

    def __post_init__(self) -> None:
        _text(self.question, 2048)
        _paths(self.targets)
        if type(self.context) is not ExecutionContext:
            raise TypeError("analysis requires ExecutionContext")


@dataclass(frozen=True, slots=True)
class RepositoryEvidence:
    """Supplied read observations, not canonical Evidence or an atomic snapshot."""

    files: tuple[RepositoryText, ...] = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.files) is not tuple:
            raise TypeError("evidence requires RepositoryText tuple")
        if not 1 <= len(self.files) <= 8:
            raise ValueError("evidence requires one to eight files")
        if any(type(f) is not RepositoryText for f in self.files):
            raise TypeError("evidence requires RepositoryText")
        _paths(tuple(RepositoryPath(f.path) for f in self.files))
        if tuple(f.path for f in self.files) != tuple(
            sorted(f.path for f in self.files)
        ):
            raise ValueError("evidence must be sorted by path")
        total = 0
        for file in self.files:
            if len(file.text) > 8192:
                raise ValueError("evidence file exceeds budget")
            try:
                size = len(file.text.encode("utf-8"))
            except UnicodeEncodeError:
                raise ValueError("evidence must be UTF-8") from None
            if size > 8192:
                raise ValueError("evidence file exceeds budget")
            total += size
        if total > 24576:
            raise ValueError("evidence exceeds total budget")


@dataclass(frozen=True, slots=True)
class RepositoryFinding:
    text: str = field(repr=False)
    paths: tuple[RepositoryPath, ...]

    def __post_init__(self) -> None:
        _text(self.text, 1024)
        _paths(self.paths)


class RepositoryAnalysisStatus(Enum):
    SUCCEEDED = "succeeded"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    MODEL_FAILURE = "model_failure"
    OUTPUT_INVALID = "output_invalid"


class AcquisitionFailure(Enum):
    DENIED = "denied"
    UNAVAILABLE = "unavailable"
    BOUNDARY = "boundary"
    BUDGET = "budget"


class EvidenceAcquisitionError(ValueError):
    def __init__(self, reason: AcquisitionFailure) -> None:
        if type(reason) is not AcquisitionFailure:
            raise TypeError("acquisition error requires AcquisitionFailure")
        self.reason = reason
        super().__init__(reason.value)


@dataclass(frozen=True, slots=True)
class RepositoryAnalysis:
    """Untrusted narrative with validated evidence-member citations."""

    summary: str = field(repr=False)
    relevant_files: tuple[RepositoryPath, ...]
    findings: tuple[RepositoryFinding, ...]
    risks: tuple[str, ...] = field(repr=False)
    unknowns: tuple[str, ...] = field(repr=False)

    def __post_init__(self) -> None:
        _text(self.summary, 2048)
        _paths(self.relevant_files, empty=True)
        if type(self.findings) is not tuple or len(self.findings) > 8:
            raise ValueError("analysis supports at most eight findings")
        if any(type(f) is not RepositoryFinding for f in self.findings):
            raise TypeError("analysis requires RepositoryFinding")
        for group in (self.risks, self.unknowns):
            if type(group) is not tuple or len(group) > 8:
                raise ValueError("analysis supports at most eight risks/unknowns")
            for text in group:
                _text(text, 1024)


@dataclass(frozen=True, slots=True)
class RepositoryAnalysisResult:
    status: RepositoryAnalysisStatus
    evidence: RepositoryEvidence | None
    agent_result: AgentResult | None
    analysis: RepositoryAnalysis | None
    acquisition_failure: AcquisitionFailure | None = None

    def __post_init__(self) -> None:
        if type(self.status) is not RepositoryAnalysisStatus:
            raise TypeError("analysis result requires status")
        if self.evidence is not None and type(self.evidence) is not RepositoryEvidence:
            raise TypeError("analysis result requires evidence")
        if self.agent_result is not None and type(self.agent_result) is not AgentResult:
            raise TypeError("analysis result requires AgentResult")
        if self.acquisition_failure is not None:
            if type(self.acquisition_failure) is not AcquisitionFailure:
                raise TypeError("analysis requires acquisition failure")
            if (
                self.status is not RepositoryAnalysisStatus.INSUFFICIENT_EVIDENCE
                or self.analysis is not None
                or self.agent_result is not None
            ):
                raise ValueError("acquisition failure cannot carry analysis")
        elif self.agent_result is None or self.evidence is None:
            raise ValueError("analysis requires evidence and Agent attribution")
        elif self.status is RepositoryAnalysisStatus.MODEL_FAILURE:
            if self.agent_result.status not in {
                AgentExecutionStatus.ROUTING_FAILED,
                AgentExecutionStatus.MODEL_FAILED,
            }:
                raise ValueError("model failure requires failed Agent invocation")
        elif self.status is RepositoryAnalysisStatus.OUTPUT_INVALID:
            if self.agent_result.status not in {
                AgentExecutionStatus.SUCCEEDED,
                AgentExecutionStatus.OUTPUT_INVALID,
            }:
                raise ValueError("output validation requires completed model response")
        if self.analysis is not None:
            if type(self.analysis) is not RepositoryAnalysis or self.evidence is None:
                raise TypeError("analysis result requires typed analysis and evidence")
            if self.status not in {
                RepositoryAnalysisStatus.SUCCEEDED,
                RepositoryAnalysisStatus.INSUFFICIENT_EVIDENCE,
            }:
                raise ValueError("failed model/output cannot carry analysis")
            if (
                self.agent_result is None
                or self.agent_result.status is not AgentExecutionStatus.SUCCEEDED
            ):
                raise ValueError("structured analysis requires successful Agent output")
            if self.status is RepositoryAnalysisStatus.INSUFFICIENT_EVIDENCE and (
                not self.analysis.unknowns or self.analysis.findings
            ):
                raise ValueError(
                    "insufficient evidence requires unknowns and no findings"
                )
            supplied = {f.path for f in self.evidence.files}
            cited = (
                *self.analysis.relevant_files,
                *(p for f in self.analysis.findings for p in f.paths),
            )
            if any(path.value not in supplied for path in cited):
                raise ValueError("analysis cites an unsupplied path")
        elif self.status is RepositoryAnalysisStatus.SUCCEEDED or (
            self.status is RepositoryAnalysisStatus.INSUFFICIENT_EVIDENCE
            and self.acquisition_failure is None
        ):
            raise ValueError("successful analysis requires structured output")
