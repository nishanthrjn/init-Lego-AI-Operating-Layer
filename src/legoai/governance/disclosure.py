"""ADR-024 remote Model disclosure governance values (`model-disclosure/1`).

Provenance classes, provider-condition facts with an explicit evidence basis,
operator disclosure admissions and one pure admission evaluator. These are
immutable records and a deterministic decision function only: nothing here
performs I/O, fetches a policy document, inspects content, resolves a Secret,
or gates an invocation. Runtime owns host configuration and (in a later slice)
the invocation-time gate. Construction grants no authority; only an operator
configuring a host supplies admissions.
"""

import urllib.parse
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum

from legoai.kernel.identity import _validate


def vocabulary() -> str:
    """The closed disclosure vocabulary identity these values implement."""
    return "model-disclosure/1"


def _max_items() -> int:
    return 16


def _max_retention_days() -> int:
    return 36_500


def _text(value: object, maximum: int = 256) -> None:
    if type(value) is not str:
        raise TypeError("disclosure text must be str")
    if (
        not 1 <= len(value) <= maximum
        or value.isspace()
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise ValueError("disclosure text is blank, oversized or has controls")


def _exact(value: object) -> None:
    """An exact operator identity: bounded text with no wildcard character."""
    _text(value)
    assert isinstance(value, str)
    if "*" in value or "?" in value or value != value.strip():
        raise ValueError("wildcards and padding are not exact identities")


def _items(values: object, kind: type, *, empty: bool = False) -> None:
    if type(values) is not frozenset:
        raise TypeError("disclosure sets must be frozenset")
    if any(type(item) is not kind for item in values):
        raise TypeError(f"disclosure set requires {kind.__name__}")
    if not (0 if empty else 1) <= len(values) <= _max_items():
        raise ValueError("disclosure set is empty or oversized")


def _aware(value: object) -> datetime:
    if type(value) is not datetime:
        raise TypeError("disclosure time must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("disclosure time must be timezone-aware")
    return value


class DisclosureClass(Enum):
    """Closed provenance vocabulary `model-disclosure/1` (ADR-024 §4).

    Provenance, not semantic sensitivity. An invocation declaring no class is
    UNCLASSIFIED (an empty declaration) and is never admitted.
    """

    SYNTHETIC = "synthetic"
    PLATFORM_INSTRUCTION = "platform_instruction"
    TASK_TEXT = "task_text"
    REPOSITORY_CONTENT = "repository_content"
    DERIVED_DIAGNOSTIC = "derived_diagnostic"


def _repository_classes() -> frozenset[DisclosureClass]:
    return frozenset(
        {DisclosureClass.REPOSITORY_CONTENT, DisclosureClass.DERIVED_DIAGNOSTIC}
    )


class FactBasis(Enum):
    """Why a fact is believed (ADR-024 §5).

    VERIFIED is reserved for properties LegoAI checks mechanically at each
    invocation (endpoint, transport, model, deployment). A declaration can
    never assert it: a policy URL or comment is not verification.
    """

    VERIFIED = "verified"
    PROVIDER_DECLARED = "provider_declared"
    OPERATOR_ATTESTED = "operator_attested"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class RepositoryIdentity:
    """Operator-declared opaque repository identity; never discovered.

    Not a filesystem path and not proof of what a workspace contains: a
    consumer binds its run to this identity under operator configuration.
    """

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _exact(self.value)


@dataclass(frozen=True, slots=True)
class SourceReference:
    """Where a provider-declared fact was read: a title or URL and the date.

    A reference only; the document is never fetched, stored or trusted.
    """

    reference: str = field(repr=False)
    retrieved_on: date

    def __post_init__(self) -> None:
        _text(self.reference, 512)
        if type(self.retrieved_on) is not date:
            raise TypeError("source reference requires a date")


class RetentionKind(Enum):
    NONE = "none"
    BOUNDED = "bounded"
    UNBOUNDED = "unbounded"
    UNKNOWN = "unknown"


class TrainingUse(Enum):
    NO = "no"
    NO_BY_CONFIGURATION = "no_by_configuration"
    YES = "yes"
    UNKNOWN = "unknown"


class HumanAccess(Enum):
    NONE = "none"
    RESTRICTED = "restricted"
    YES = "yes"
    UNKNOWN = "unknown"


class SubprocessorsKind(Enum):
    DECLARED = "declared"
    NOT_MATERIAL = "not_material"
    UNKNOWN = "unknown"


def _basis(basis: object, source: object, known: bool) -> None:
    if type(basis) is not FactBasis:
        raise TypeError("fact requires FactBasis")
    if source is not None and type(source) is not SourceReference:
        raise TypeError("fact source must be SourceReference or None")
    if basis is FactBasis.VERIFIED:
        raise ValueError("a declaration cannot assert mechanical verification")
    if known != (basis is not FactBasis.UNKNOWN):
        raise ValueError("fact value and basis must agree on UNKNOWN")
    if basis is FactBasis.UNKNOWN and source is not None:
        raise ValueError("an unknown fact has no source")
    if basis is FactBasis.PROVIDER_DECLARED and source is None:
        raise ValueError("a provider-declared fact requires its source reference")


@dataclass(frozen=True, slots=True)
class ProcessorIdentityFact:
    """Legal or service name of the processor operating the endpoint."""

    name: str | None = field(repr=False)
    basis: FactBasis
    source: SourceReference | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.name is not None:
            _text(self.name)
        _basis(self.basis, self.source, self.name is not None)

    @property
    def known(self) -> bool:
        return self.name is not None


@dataclass(frozen=True, slots=True)
class LocationFact:
    """Processing location / residency as jurisdiction or region labels."""

    regions: frozenset[str] | None = field(repr=False)
    basis: FactBasis
    source: SourceReference | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.regions is not None:
            _items(self.regions, str)
            for region in self.regions:
                _exact(region)
        _basis(self.basis, self.source, self.regions is not None)

    @property
    def known(self) -> bool:
        return self.regions is not None


@dataclass(frozen=True, slots=True)
class RetentionFact:
    """Retention of inputs and outputs, including provider-side content logs."""

    kind: RetentionKind
    max_days: int | None
    basis: FactBasis
    source: SourceReference | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.kind) is not RetentionKind:
            raise TypeError("retention requires RetentionKind")
        if (self.kind is RetentionKind.BOUNDED) != (self.max_days is not None):
            raise ValueError("only bounded retention states a maximum")
        if self.max_days is not None and (
            type(self.max_days) is not int
            or not 0 <= self.max_days <= _max_retention_days()
        ):
            raise ValueError("retention maximum must be a bounded day count")
        _basis(self.basis, self.source, self.known)

    @property
    def known(self) -> bool:
        return self.kind is not RetentionKind.UNKNOWN


@dataclass(frozen=True, slots=True)
class TrainingFact:
    value: TrainingUse
    basis: FactBasis
    source: SourceReference | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.value) is not TrainingUse:
            raise TypeError("training fact requires TrainingUse")
        _basis(self.basis, self.source, self.known)
        if (
            self.value is TrainingUse.NO_BY_CONFIGURATION
            and self.basis is not FactBasis.OPERATOR_ATTESTED
        ):
            raise ValueError("an opt-out in effect is an operator attestation")

    @property
    def known(self) -> bool:
        return self.value is not TrainingUse.UNKNOWN


@dataclass(frozen=True, slots=True)
class HumanAccessFact:
    value: HumanAccess
    basis: FactBasis
    source: SourceReference | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.value) is not HumanAccess:
            raise TypeError("human access fact requires HumanAccess")
        _basis(self.basis, self.source, self.known)

    @property
    def known(self) -> bool:
        return self.value is not HumanAccess.UNKNOWN


@dataclass(frozen=True, slots=True)
class SubprocessorsFact:
    kind: SubprocessorsKind
    names: frozenset[str] = field(repr=False)
    basis: FactBasis
    source: SourceReference | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.kind) is not SubprocessorsKind:
            raise TypeError("subprocessors fact requires SubprocessorsKind")
        _items(self.names, str, empty=self.kind is not SubprocessorsKind.DECLARED)
        if self.kind is not SubprocessorsKind.DECLARED and self.names:
            raise ValueError("only a declared list names subprocessors")
        for name in self.names:
            _text(name)
        _basis(self.basis, self.source, self.known)
        if (
            self.kind is SubprocessorsKind.NOT_MATERIAL
            and self.basis is not FactBasis.OPERATOR_ATTESTED
        ):
            raise ValueError("'not material' is an operator attestation")

    @property
    def known(self) -> bool:
        return self.kind is not SubprocessorsKind.UNKNOWN


def endpoint_parts(base_url: str) -> tuple[str, str] | None:
    """Normalized `(origin, api_root)` of an https API root, else None.

    The origin is `https://host[:port]` with a lowercase host and no default
    port; the API root is the path without a trailing slash. Pure parsing.
    """
    if type(base_url) is not str:
        raise TypeError("base URL must be str")
    try:
        url = urllib.parse.urlsplit(base_url)
        port = url.port
    except ValueError:
        return None
    if (
        url.scheme != "https"
        or not url.hostname
        or url.username is not None
        or url.password is not None
        or url.query
        or url.fragment
        or port == 0
        or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in base_url)
    ):
        return None
    origin = "https://" + url.hostname + (f":{port}" if port not in (None, 443) else "")
    root = url.path.rstrip("/") or "/"
    if not root.startswith("/") or "//" in root:
        return None
    return origin, root


def _endpoint(origin: object, api_root: object) -> None:
    _text(origin)
    _text(api_root)
    assert isinstance(origin, str) and isinstance(api_root, str)
    if endpoint_parts(origin + ("" if api_root == "/" else api_root)) != (
        origin,
        api_root,
    ):
        raise ValueError("endpoint must be a normalized https origin and API root")


@dataclass(frozen=True, slots=True)
class ProcessorDeclaration:
    """Operator-authored, versioned description of one remote processor.

    `provider_id` is the exact operator identity of the endpoint (the binding's
    ProviderId value). Every declared fact carries its basis. Any change is a
    new revision; an admission pins exactly one revision.
    """

    declaration_id: str = field(repr=False)
    revision: str = field(repr=False)
    provider_id: str = field(repr=False)
    endpoint_origin: str = field(repr=False)
    api_root: str = field(repr=False)
    processor: ProcessorIdentityFact
    location: LocationFact
    retention: RetentionFact
    training: TrainingFact
    human_access: HumanAccessFact
    subprocessors: SubprocessorsFact

    def __post_init__(self) -> None:
        _validate(self.declaration_id)
        _validate(self.revision)
        _exact(self.provider_id)
        _endpoint(self.endpoint_origin, self.api_root)
        for value, kind in (
            (self.processor, ProcessorIdentityFact),
            (self.location, LocationFact),
            (self.retention, RetentionFact),
            (self.training, TrainingFact),
            (self.human_access, HumanAccessFact),
            (self.subprocessors, SubprocessorsFact),
        ):
            if type(value) is not kind:
                raise TypeError(f"declaration requires {kind.__name__}")


@dataclass(frozen=True, slots=True)
class ClassConditions:
    """The operator's acceptable provider conditions for one disclosure class.

    Only tightens ADR-024 §5.2: a mandatory fact can never be accepted as
    UNKNOWN. Subprocessors are mandatory only for repository classes, so
    `subprocessors=None` (not evaluated) is allowed only for the others.
    """

    disclosure_class: DisclosureClass
    locations: frozenset[str] = field(repr=False)
    retention: frozenset[RetentionKind]
    max_retention_days: int | None
    training: frozenset[TrainingUse]
    human_access: frozenset[HumanAccess]
    subprocessors: frozenset[SubprocessorsKind] | None

    def __post_init__(self) -> None:
        if type(self.disclosure_class) is not DisclosureClass:
            raise TypeError("conditions require DisclosureClass")
        if self.disclosure_class is DisclosureClass.SYNTHETIC:
            raise ValueError("SYNTHETIC has no mandatory provider conditions")
        _items(self.locations, str)
        for region in self.locations:
            _exact(region)
        _items(self.retention, RetentionKind)
        _items(self.training, TrainingUse)
        _items(self.human_access, HumanAccess)
        if (
            RetentionKind.UNKNOWN in self.retention
            or TrainingUse.UNKNOWN in self.training
            or HumanAccess.UNKNOWN in self.human_access
        ):
            raise ValueError("a mandatory fact cannot be accepted as UNKNOWN")
        if (RetentionKind.BOUNDED in self.retention) != (
            self.max_retention_days is not None
        ):
            raise ValueError("a bound is stated exactly when BOUNDED is accepted")
        if self.max_retention_days is not None and (
            type(self.max_retention_days) is not int
            or not 0 <= self.max_retention_days <= _max_retention_days()
        ):
            raise ValueError("retention bound must be a bounded day count")
        if self.subprocessors is None:
            if self.disclosure_class in _repository_classes():
                raise ValueError("repository classes require subprocessor conditions")
        else:
            _items(self.subprocessors, SubprocessorsKind)
            if SubprocessorsKind.UNKNOWN in self.subprocessors:
                raise ValueError("accepting UNKNOWN subprocessors is not a condition")


@dataclass(frozen=True, slots=True)
class DisclosureAdmission:
    """Explicit, revisioned operator admission (ADR-024 §6). No defaults.

    Exact bindings, provider, endpoint, models, consumer and purposes; one
    pinned declaration revision; permitted classes with conditions for every
    non-SYNTHETIC class; repository identities exactly when repository
    classes are permitted; a mandatory validity window. Deployment is REMOTE
    by construction: host validation admits only REMOTE-declared bindings.
    """

    admission_id: str = field(repr=False)
    revision: str = field(repr=False)
    bindings: frozenset[str] = field(repr=False)
    provider_id: str = field(repr=False)
    endpoint_origin: str = field(repr=False)
    api_root: str = field(repr=False)
    models: frozenset[str] = field(repr=False)
    consumer: str = field(repr=False)
    purposes: frozenset[str]
    declaration_id: str = field(repr=False)
    declaration_revision: str = field(repr=False)
    classes: frozenset[DisclosureClass]
    conditions: tuple[ClassConditions, ...] = field(repr=False)
    repositories: frozenset[RepositoryIdentity] = field(repr=False)
    not_before: datetime
    not_after: datetime

    def __post_init__(self) -> None:
        _validate(self.admission_id)
        _validate(self.revision)
        _items(self.bindings, str)
        for value in self.bindings:
            _exact(value)
        _exact(self.provider_id)
        _endpoint(self.endpoint_origin, self.api_root)
        _items(self.models, str)
        for model in self.models:
            _exact(model)
        _exact(self.consumer)
        _items(self.purposes, str)
        for purpose in self.purposes:
            _exact(purpose)
        _validate(self.declaration_id)
        _validate(self.declaration_revision)
        _items(self.classes, DisclosureClass)
        if (
            DisclosureClass.DERIVED_DIAGNOSTIC in self.classes
            and DisclosureClass.REPOSITORY_CONTENT not in self.classes
        ):
            raise ValueError("derived diagnostics require repository content")
        if type(self.conditions) is not tuple or any(
            type(item) is not ClassConditions for item in self.conditions
        ):
            raise TypeError("admission conditions require ClassConditions")
        covered = [item.disclosure_class for item in self.conditions]
        if len(set(covered)) != len(covered) or set(covered) != (
            self.classes - {DisclosureClass.SYNTHETIC}
        ):
            raise ValueError("exactly one condition set per non-SYNTHETIC class")
        _items(
            self.repositories,
            RepositoryIdentity,
            empty=not self.classes & _repository_classes(),
        )
        if bool(self.repositories) != bool(self.classes & _repository_classes()):
            raise ValueError("repositories are named exactly for repository classes")
        if _aware(self.not_after) <= _aware(self.not_before):
            raise ValueError("admission validity window must be ordered")

    def conditions_for(self, disclosure_class: DisclosureClass) -> ClassConditions:
        return next(
            c for c in self.conditions if c.disclosure_class is disclosure_class
        )


@dataclass(frozen=True, slots=True)
class DisclosureDeclaration:
    """The provenance classes of one invocation, assigned by trusted code.

    Empty classes means UNCLASSIFIED. A repository identity is named exactly
    when a repository class is declared.
    """

    classes: frozenset[DisclosureClass]
    repository: RepositoryIdentity | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        _items(self.classes, DisclosureClass, empty=True)
        if self.repository is not None and type(self.repository) is not (
            RepositoryIdentity
        ):
            raise TypeError("repository must be RepositoryIdentity or None")
        if (self.repository is not None) != bool(self.classes & _repository_classes()):
            raise ValueError("a repository is named exactly for repository classes")

    @property
    def unclassified(self) -> bool:
        return not self.classes


@dataclass(frozen=True, slots=True)
class DisclosureRequest:
    """Observed facts of one prospective remote invocation, supplied by the
    trusted invocation plane; never by model output or content."""

    binding_id: str = field(repr=False)
    provider_id: str = field(repr=False)
    endpoint_origin: str = field(repr=False)
    api_root: str = field(repr=False)
    remote: bool
    model: str = field(repr=False)
    consumer: str = field(repr=False)
    purpose: str
    declaration: DisclosureDeclaration
    at: datetime

    def __post_init__(self) -> None:
        for value in (
            self.binding_id,
            self.provider_id,
            self.endpoint_origin,
            self.api_root,
            self.model,
            self.consumer,
            self.purpose,
        ):
            _text(value)
        if type(self.remote) is not bool:
            raise TypeError("remote must be bool")
        if type(self.declaration) is not DisclosureDeclaration:
            raise TypeError("request requires DisclosureDeclaration")
        _aware(self.at)


class DisclosureRefusal(Enum):
    """Closed refusal taxonomy for the pure evaluator (ADR-024 §7)."""

    NO_ADMISSION = "no_admission"
    NOT_YET_VALID = "not_yet_valid"
    EXPIRED = "expired"
    PROVIDER_MISMATCH = "provider_mismatch"
    ENDPOINT_MISMATCH = "endpoint_mismatch"
    API_ROOT_MISMATCH = "api_root_mismatch"
    DEPLOYMENT_MISMATCH = "deployment_mismatch"
    MODEL_NOT_ADMITTED = "model_not_admitted"
    CONSUMER_MISMATCH = "consumer_mismatch"
    PURPOSE_MISMATCH = "purpose_mismatch"
    UNCLASSIFIED = "unclassified"
    CLASS_NOT_ADMITTED = "class_not_admitted"
    REPOSITORY_NOT_ADMITTED = "repository_not_admitted"
    DECLARATION_STALE = "declaration_stale"
    REQUIRED_FACT_UNKNOWN = "required_fact_unknown"
    CONDITION_UNMET = "condition_unmet"


@dataclass(frozen=True, slots=True)
class DisclosureDecision:
    """Point-in-time evaluation result, never a reusable permit."""

    refusal: DisclosureRefusal | None
    admission_id: str | None = field(default=None, repr=False)
    admission_revision: str | None = field(default=None, repr=False)
    declaration_revision: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.refusal is not None and type(self.refusal) is not DisclosureRefusal:
            raise TypeError("refusal must be DisclosureRefusal or None")
        if self.refusal is None and (
            self.admission_id is None or self.declaration_revision is None
        ):
            raise ValueError("an admitted decision names its admission")

    @property
    def admitted(self) -> bool:
        return self.refusal is None


def _facts(
    declaration: ProcessorDeclaration,
    admission: DisclosureAdmission,
    classes: frozenset[DisclosureClass],
) -> DisclosureRefusal | None:
    if not declaration.processor.known:
        return DisclosureRefusal.REQUIRED_FACT_UNKNOWN
    for disclosure_class in sorted(classes, key=lambda item: item.value):
        if disclosure_class is DisclosureClass.SYNTHETIC:
            continue  # ADR-024 §5.2: only provider identity is mandatory.
        known = [
            declaration.location.known,
            declaration.retention.known,
            declaration.training.known,
            declaration.human_access.known,
        ]
        if disclosure_class in _repository_classes():
            known.append(declaration.subprocessors.known)
        if not all(known):
            return DisclosureRefusal.REQUIRED_FACT_UNKNOWN
        wanted = admission.conditions_for(disclosure_class)
        retention = declaration.retention
        regions = declaration.location.regions
        assert regions is not None
        if (
            not regions <= wanted.locations
            or retention.kind not in wanted.retention
            or (
                retention.max_days is not None
                and wanted.max_retention_days is not None
                and retention.max_days > wanted.max_retention_days
            )
            or declaration.training.value not in wanted.training
            or declaration.human_access.value not in wanted.human_access
            or (
                wanted.subprocessors is not None
                and declaration.subprocessors.kind not in wanted.subprocessors
            )
        ):
            return DisclosureRefusal.CONDITION_UNMET
    return None


def evaluate_disclosure(
    request: DisclosureRequest,
    admissions: tuple[DisclosureAdmission, ...],
    declarations: tuple[ProcessorDeclaration, ...],
) -> DisclosureDecision:
    """Pure decision: may this content go to this remote processor now?

    No I/O, no mutation, no global state. Expected refusals are returned as
    a typed decision, never raised. Checks run in a fixed order; the first
    failing rule is reported.
    """
    if type(request) is not DisclosureRequest:
        raise TypeError("evaluation requires DisclosureRequest")
    if type(admissions) is not tuple or any(
        type(item) is not DisclosureAdmission for item in admissions
    ):
        raise TypeError("evaluation requires a tuple of DisclosureAdmission")
    if type(declarations) is not tuple or any(
        type(item) is not ProcessorDeclaration for item in declarations
    ):
        raise TypeError("evaluation requires a tuple of ProcessorDeclaration")
    matching = [a for a in admissions if request.binding_id in a.bindings]
    if len(matching) != 1:
        # None, or an ambiguous configuration: refuse rather than choose.
        return DisclosureDecision(DisclosureRefusal.NO_ADMISSION)
    admission = matching[0]

    def refuse(reason: DisclosureRefusal) -> DisclosureDecision:
        return DisclosureDecision(reason, admission.admission_id, admission.revision)

    if request.at < admission.not_before:
        return refuse(DisclosureRefusal.NOT_YET_VALID)
    if request.at >= admission.not_after:
        return refuse(DisclosureRefusal.EXPIRED)
    current = [d for d in declarations if d.declaration_id == admission.declaration_id]
    if len(current) != 1 or current[0].revision != admission.declaration_revision:
        return refuse(DisclosureRefusal.DECLARATION_STALE)
    declaration = current[0]
    if not request.provider_id == admission.provider_id == declaration.provider_id:
        return refuse(DisclosureRefusal.PROVIDER_MISMATCH)
    if not (
        request.endpoint_origin
        == admission.endpoint_origin
        == declaration.endpoint_origin
    ):
        return refuse(DisclosureRefusal.ENDPOINT_MISMATCH)
    if not request.api_root == admission.api_root == declaration.api_root:
        return refuse(DisclosureRefusal.API_ROOT_MISMATCH)
    if not request.remote:
        return refuse(DisclosureRefusal.DEPLOYMENT_MISMATCH)
    if request.model not in admission.models:
        return refuse(DisclosureRefusal.MODEL_NOT_ADMITTED)
    if request.consumer != admission.consumer:
        return refuse(DisclosureRefusal.CONSUMER_MISMATCH)
    if request.purpose not in admission.purposes:
        return refuse(DisclosureRefusal.PURPOSE_MISMATCH)
    classes = request.declaration.classes
    if not classes:
        return refuse(DisclosureRefusal.UNCLASSIFIED)
    if not classes <= admission.classes or (
        # Lineage (SEC-067): derived diagnostics travel only where their
        # source repository content is admitted for the same repository.
        DisclosureClass.DERIVED_DIAGNOSTIC in classes
        and DisclosureClass.REPOSITORY_CONTENT not in admission.classes
    ):
        return refuse(DisclosureRefusal.CLASS_NOT_ADMITTED)
    repository = request.declaration.repository
    if repository is not None and repository not in admission.repositories:
        return refuse(DisclosureRefusal.REPOSITORY_NOT_ADMITTED)
    unmet = _facts(declaration, admission, classes)
    if unmet is not None:
        return refuse(unmet)
    return DisclosureDecision(
        None, admission.admission_id, admission.revision, declaration.revision
    )
