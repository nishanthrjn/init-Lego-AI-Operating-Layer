"""One operator-selected round, with no model invocation or target authority."""

from dataclasses import dataclass, field, replace
from enum import Enum

from legoai_engineering.analyst.api import RepositoryEvidencePort
from legoai_engineering.analyst.authorized import AuthorizedRepositoryEvidence
from legoai_engineering.analyst.sufficiency import (
    EvidenceClarification,
    EvidenceManifest,
    EvidenceRequestKind,
    EvidenceSufficiencyAssessment,
    EvidenceSufficiencyError,
    EvidenceSufficiencyResult,
    SufficiencyDisposition,
    SufficiencyFailure,
)
from legoai_engineering.analyst.values import (
    AcquisitionFailure,
    EvidenceAcquisitionError,
    RepositoryEvidence,
)
from legoai_engineering.repository.workspace import RepositoryPath

from legoai.execution.values import ExecutionId
from legoai.kernel.context import TenantContext


class Stage(Enum):
    ASSESS = "assess"
    REVIEW = "review"
    ACQUIRING = "acquiring"
    ELIGIBLE_FOR_ANALYSIS = "eligible_for_analysis"
    STOPPED = "stopped"


class StopReason(Enum):
    OPERATOR_DECLINED = "operator_declined"
    UNRESOLVED = "unresolved"
    INVALID_REVIEW = "invalid_review"
    DUPLICATE_INVOCATION = "duplicate_invocation"
    INVALID_SEQUENCE = "invalid_sequence"
    OPERATIONAL_FAILURE = "operational_failure"


@dataclass(frozen=True, slots=True)
class OperatorReview:
    """Trusted operator input, not a grant, model output or signed credential."""

    manifest_identity: str = field(repr=False)
    assessment_id: ExecutionId
    accepted: bool

    def __post_init__(self) -> None:
        if (
            type(self.accepted) is not bool
            or type(self.assessment_id) is not ExecutionId
        ):
            raise TypeError("typed operator review required")
        if type(self.manifest_identity) is not str or len(self.manifest_identity) != 64:
            raise ValueError("manifest identity required")


@dataclass(frozen=True, slots=True)
class PathSelection:
    """Operator mapping of one current request to one exact known path."""

    request_index: int
    path: RepositoryPath = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.request_index) is not int or not 0 <= self.request_index < 8:
            raise ValueError("bounded request index required")
        if type(self.path) is not RepositoryPath:
            raise TypeError("exact operator path required")


@dataclass(frozen=True, slots=True)
class ClarificationSelection:
    request_index: int
    answer: str = field(repr=False)
    question: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.request_index) is not int or not 0 <= self.request_index < 8:
            raise ValueError("bounded request index required")
        for value, limit in ((self.answer, 1024), (self.question, 2048)):
            if type(value) is not str or not value.strip() or len(value) > limit:
                raise ValueError("bounded nonblank operator text required")
            try:
                size = len(value.encode("utf-8"))
            except UnicodeEncodeError:
                raise ValueError("operator text must be UTF-8") from None
            if size > limit:
                raise ValueError("operator text exceeds byte bound")


@dataclass(frozen=True, slots=True)
class RoundRecord:
    before: str = field(repr=False)
    after: str = field(repr=False)
    paths: tuple[PathSelection, ...] = field(repr=False)
    clarification: ClarificationSelection | None = field(repr=False)


@dataclass(frozen=True, slots=True)
class Observation:
    stage: Stage
    manifest: EvidenceManifest = field(repr=False)
    assessment: EvidenceSufficiencyAssessment | None = field(repr=False)
    assessment_ids: tuple[ExecutionId, ...]
    analysis_ids: tuple[ExecutionId, ...]
    rounds: int
    reviews: tuple[OperatorReview, ...] = field(repr=False)
    failure: SufficiencyFailure | None
    stop_reason: StopReason | None
    assessments: tuple[EvidenceSufficiencyAssessment, ...] = field(repr=False)
    round_record: RoundRecord | None = field(repr=False)


class EvidenceSequence:
    """Ephemeral, single-sequence scripted evaluation. No persistence/resumption.

    Limits are fixed: two assessment claims, one analysis claim, one round.
    An analysis claim records a scripted call slot only; it never invokes Analyst.
    Current manifests are caller observations, not a filesystem freshness oracle.
    """

    def __init__(
        self,
        initial: EvidenceManifest,
        reader: AuthorizedRepositoryEvidence,
        tenant: TenantContext,
    ) -> None:
        if type(initial) is not EvidenceManifest or type(tenant) is not TenantContext:
            raise TypeError("manifest and tenant required")
        if type(reader) is not AuthorizedRepositoryEvidence:
            raise TypeError("authorized evidence composition required")
        self._reader: RepositoryEvidencePort = reader
        self._tenant = tenant
        self._manifest = initial
        self._assessment: EvidenceSufficiencyAssessment | None = None
        self._stage = Stage.ASSESS
        self._assessment_ids: list[ExecutionId] = []
        self._analysis_ids: list[ExecutionId] = []
        self._rounds = 0
        self._reviews: list[OperatorReview] = []
        self._failure: SufficiencyFailure | None = None
        self._stop_reason: StopReason | None = None
        self._assessments: list[EvidenceSufficiencyAssessment] = []
        self._round_record: RoundRecord | None = None

    def observe(self) -> Observation:
        return Observation(
            self._stage,
            self._manifest,
            self._assessment,
            tuple(self._assessment_ids),
            tuple(self._analysis_ids),
            self._rounds,
            tuple(self._reviews),
            self._failure,
            self._stop_reason,
            tuple(self._assessments),
            self._round_record,
        )

    def _stop(
        self,
        reason: StopReason,
        failure: SufficiencyFailure | None = None,
    ) -> Observation:
        # First failure is retained; a stopped sequence cannot be revived.
        if self._stage is not Stage.STOPPED:
            self._stage, self._stop_reason, self._failure = (
                Stage.STOPPED,
                reason,
                failure,
            )
        return self.observe()

    def _fail(self, failure: SufficiencyFailure) -> Observation:
        return self._stop(StopReason.OPERATIONAL_FAILURE, failure)

    def _claim(self, identity: ExecutionId, *, analysis: bool = False) -> bool:
        if type(identity) is not ExecutionId:
            self._fail(SufficiencyFailure.INVALID_OUTPUT)
            return False
        if identity in (*self._assessment_ids, *self._analysis_ids):
            self._stop(StopReason.DUPLICATE_INVOCATION)
            return False
        claimed = self._analysis_ids if analysis else self._assessment_ids
        if len(claimed) >= (1 if analysis else 2):
            self._fail(SufficiencyFailure.BUDGET_EXHAUSTED)
            return False
        claimed.append(identity)
        return True

    def assess(self, identity: ExecutionId, result: object) -> Observation:
        """Accept one scripted output; no callback, dispatch, retry or repair."""
        if self._stage is Stage.STOPPED:
            return self.observe()
        if len(self._assessment_ids) >= 2:
            return self._fail(SufficiencyFailure.BUDGET_EXHAUSTED)
        if self._stage is not Stage.ASSESS:
            return self._stop(StopReason.INVALID_SEQUENCE)
        if not self._claim(identity):
            return self.observe()
        if type(result) is not EvidenceSufficiencyResult:
            return self._fail(SufficiencyFailure.INVALID_OUTPUT)
        if result.failure is not None:
            return self._fail(result.failure)
        assert result.assessment is not None
        try:
            result.assessment.validate_for(self._manifest)
        except EvidenceSufficiencyError as error:
            return self._fail(error.reason)
        self._assessment = result.assessment
        self._assessments.append(result.assessment)
        if (
            self._rounds
            and self._assessment.disposition is not SufficiencyDisposition.SUFFICIENT
        ):
            return self._stop(StopReason.UNRESOLVED)
        self._stage = Stage.REVIEW
        return self.observe()

    def _review(self, review: OperatorReview, current: EvidenceManifest) -> bool:
        if type(review) is not OperatorReview or type(current) is not EvidenceManifest:
            self._stop(StopReason.INVALID_REVIEW)
            return False
        if (
            current.identity() != self._manifest.identity()
            or review.manifest_identity != current.identity()
            or not self._assessment_ids
            or review.assessment_id != self._assessment_ids[-1]
        ):
            self._fail(SufficiencyFailure.STALE_ASSESSMENT)
            return False
        assert self._assessment is not None
        try:
            self._assessment.validate_for(current)
        except EvidenceSufficiencyError as error:
            self._fail(error.reason)
            return False
        self._reviews.append(review)
        if not review.accepted:
            self._stop(StopReason.OPERATOR_DECLINED)
            return False
        return True

    def progress(
        self, review: OperatorReview, current: EvidenceManifest
    ) -> Observation:
        if self._stage is Stage.STOPPED:
            return self.observe()
        if self._stage is not Stage.REVIEW:
            return self._stop(StopReason.INVALID_SEQUENCE)
        if not self._review(review, current):
            return self.observe()
        assert self._assessment is not None
        if self._assessment.disposition is not SufficiencyDisposition.SUFFICIENT:
            return self._stop(StopReason.UNRESOLVED)
        self._stage = Stage.ELIGIBLE_FOR_ANALYSIS
        return self.observe()

    async def advance(
        self,
        review: OperatorReview,
        current: EvidenceManifest,
        *,
        paths: tuple[PathSelection, ...] = (),
        clarification: ClarificationSelection | None = None,
    ) -> Observation:
        """Consume the single round before any await; acquisition OR clarification."""
        if self._stage is Stage.STOPPED:
            return self.observe()
        if self._rounds:
            return self._fail(SufficiencyFailure.BUDGET_EXHAUSTED)
        if self._stage is not Stage.REVIEW:
            return self._stop(StopReason.INVALID_SEQUENCE)
        if not self._review(review, current):
            return self.observe()
        assert self._assessment is not None
        if self._assessment.disposition is SufficiencyDisposition.SUFFICIENT:
            return self._stop(StopReason.INVALID_SEQUENCE)
        try:
            if (
                type(paths) is not tuple
                or len(paths) > 8
                or bool(paths) == (clarification is not None)
            ):
                raise ValueError("one action kind required")
            if clarification is not None:
                revised = self._clarify(clarification)
            else:
                targets = self._selected_paths(paths)
                if len(current.evidence.files) + len(targets) > 8:
                    return self._fail(SufficiencyFailure.BUDGET_EXHAUSTED)
                # Reserve before yielding; reentrant/duplicate actions fail closed.
                self._rounds = 1
                self._stage = Stage.ACQUIRING
                try:
                    added = await self._reader.acquire(targets, self._tenant)
                except EvidenceAcquisitionError:
                    raise
                except BaseException:
                    self._fail(SufficiencyFailure.EVIDENCE_UNAVAILABLE)
                    raise
                if self._stage is Stage.STOPPED:
                    return self.observe()
                if type(added) is not RepositoryEvidence or {
                    f.path for f in added.files
                } != {p.value for p in targets}:
                    return self._fail(SufficiencyFailure.INVALID_OUTPUT)
                try:
                    combined = RepositoryEvidence(
                        tuple(
                            sorted(
                                (*current.evidence.files, *added.files),
                                key=lambda f: f.path,
                            )
                        )
                    )
                except ValueError:
                    return self._fail(SufficiencyFailure.BUDGET_EXHAUSTED)
                bindings = {
                    self._assessment.requests[s.request_index]: s.path for s in paths
                }
                revised = replace(
                    current,
                    evidence=combined,
                    expectations=tuple(
                        replace(e, supplied_paths=(bindings[e.request],))
                        if e.request.kind is EvidenceRequestKind.SOURCE_ROLE
                        and e.request in bindings
                        else e
                        for e in current.expectations
                    ),
                )
            if revised.identity() == current.identity():
                return self._fail(SufficiencyFailure.STALE_ASSESSMENT)
        except EvidenceAcquisitionError as error:
            return self._fail(
                {
                    AcquisitionFailure.DENIED: SufficiencyFailure.ACQUISITION_DENIED,
                    AcquisitionFailure.UNAVAILABLE: SufficiencyFailure.EVIDENCE_UNAVAILABLE,
                    AcquisitionFailure.BOUNDARY: SufficiencyFailure.AUTHORIZATION_FAILURE,
                    AcquisitionFailure.BUDGET: SufficiencyFailure.BUDGET_EXHAUSTED,
                }[error.reason]
            )
        except TypeError, ValueError, IndexError:
            if self._stage is Stage.STOPPED:
                raise
            return self._stop(StopReason.INVALID_REVIEW)
        except BaseException:
            # Preserve unexpected causes/cancellation while forbidding reuse.
            self._fail(SufficiencyFailure.EVIDENCE_UNAVAILABLE)
            raise
        self._rounds = 1
        self._round_record = RoundRecord(
            current.identity(), revised.identity(), paths, clarification
        )
        self._manifest = revised
        self._assessment = None
        self._stage = Stage.ASSESS
        return self.observe()

    def _selected_paths(
        self, selections: tuple[PathSelection, ...]
    ) -> tuple[RepositoryPath, ...]:
        assert self._assessment is not None
        if any(type(s) is not PathSelection for s in selections):
            raise TypeError("operator selections required")
        if len({s.request_index for s in selections}) != len(selections):
            raise ValueError("duplicate request selection")
        targets = tuple(s.path for s in selections)
        names = {p.value.casefold() for p in targets}
        if len(names) != len(targets) or names & {
            f.path.casefold() for f in self._manifest.evidence.files
        }:
            raise ValueError("only distinct explicitly added files are supported")
        for selection in selections:
            request = self._assessment.requests[selection.request_index]
            if request.kind is EvidenceRequestKind.OPERATOR_CLARIFICATION:
                raise ValueError("clarification is not a read")
            if (
                request.kind is EvidenceRequestKind.NAMED_EVIDENCE
                and request.path != selection.path
            ):
                raise ValueError("named path must match exactly")
        return targets

    def _clarify(self, selection: ClarificationSelection) -> EvidenceManifest:
        assert self._assessment is not None
        if type(selection) is not ClarificationSelection:
            raise TypeError("operator clarification required")
        request = self._assessment.requests[selection.request_index]
        if request.kind is not EvidenceRequestKind.OPERATOR_CLARIFICATION:
            raise ValueError("clarification request required")
        entries = tuple(
            replace(c, answer=selection.answer) if c.request == request else c
            for c in self._manifest.clarifications
        )
        if not any(c.request == request for c in entries):
            entries += (
                EvidenceClarification("loop-clarification", request, selection.answer),
            )
        return replace(
            self._manifest, question=selection.question, clarifications=entries
        )

    def claim_scripted_analysis(
        self, identity: ExecutionId, current: EvidenceManifest
    ) -> Observation:
        """Account for at most one fake final call. No Analyst or model dispatch."""
        if self._stage is Stage.STOPPED:
            return self.observe()
        if self._stage is not Stage.ELIGIBLE_FOR_ANALYSIS:
            return self._stop(StopReason.INVALID_SEQUENCE)
        if (
            type(current) is not EvidenceManifest
            or current.identity() != self._manifest.identity()
        ):
            return self._fail(SufficiencyFailure.STALE_ASSESSMENT)
        self._claim(identity, analysis=True)
        return self.observe()
