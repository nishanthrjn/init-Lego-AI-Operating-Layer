"""Bounded operator policy data for the existing governed REMOTE Model path.

No transport or credential material lives here.
The CLI profile supports explicit operator attestations only; it never
infers provider guarantees from an endpoint or a provider name.
"""

import hashlib
import json
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from legoai.governance.disclosure import (
    ClassConditions,
    DisclosureAdmission,
    DisclosureClass,
    DisclosureDeclaration,
    DisclosureRequest,
    FactBasis,
    HumanAccess,
    HumanAccessFact,
    LocationFact,
    ProcessorDeclaration,
    ProcessorIdentityFact,
    RepositoryIdentity,
    RetentionFact,
    RetentionKind,
    SubprocessorsFact,
    SubprocessorsKind,
    TrainingFact,
    TrainingUse,
    endpoint_parts,
    evaluate_disclosure,
)
from legoai.intelligence.model.routing import ModelRequirement
from legoai.intelligence.model.values import ProviderId
from legoai.runtime.api import (
    ExecutionDisclosure,
    ModelBindingConfig,
    ModelDeployment,
    OpenAICompatibleSettings,
    RemoteDisclosureConfig,
)

from forgeai.domain import TaskRequest

BINDING = "openai-compatible-remote"
CONSUMER = "forgeai"


def classes(*, derived: bool) -> frozenset[DisclosureClass]:
    values = frozenset(
        {
            DisclosureClass.PLATFORM_INSTRUCTION,
            DisclosureClass.TASK_TEXT,
            DisclosureClass.REPOSITORY_CONTENT,
        }
    )
    return values | {DisclosureClass.DERIVED_DIAGNOSTIC} if derived else values


def task_digest(task: TaskRequest) -> str:
    value = (
        task.objective,
        task.constraints,
        tuple((t.path.value, t.operation.value) for t in task.targets),
        tuple(p.value for p in task.context),
    )
    return hashlib.sha256(json.dumps(value, ensure_ascii=True).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class RemoteProfile:
    """Exact non-secret binding and existing disclosure values, supplied by operator."""

    base_url: str
    model: str
    provider: ProviderId
    repository: RepositoryIdentity
    policy: RemoteDisclosureConfig = field(repr=False)
    timeout: float = 120.0

    def __post_init__(self) -> None:
        if endpoint_parts(self.base_url) is None:
            raise ValueError("remote profile requires an exact HTTPS API root")
        if (
            type(self.provider) is not ProviderId
            or type(self.repository) is not RepositoryIdentity
        ):
            raise TypeError("remote profile requires typed identities")
        if type(self.policy) is not RemoteDisclosureConfig:
            raise TypeError("remote profile requires disclosure policy")
        if type(self.timeout) not in (int, float) or not 1 <= self.timeout <= 300:
            raise ValueError("remote timeout must be 1..300 seconds")
        # Reuse the existing exact model/endpoint validation at host open too.
        if (
            not self.model
            or len(self.model) > 256
            or any(not c.isprintable() or c in "*?" for c in self.model)
            or self.model != self.model.strip()
        ):
            raise ValueError("remote model must be an exact bounded id")

    def binding(self) -> ModelBindingConfig:
        return ModelBindingConfig(
            BINDING,
            ModelRequirement("engineering-reasoning"),
            OpenAICompatibleSettings(
                self.base_url,
                self.model,
                None,
                self.timeout,
                None,
                self.provider,
                ModelDeployment.REMOTE,
            ),
        )

    def disclosure(self, *, derived: bool) -> ExecutionDisclosure:
        return ExecutionDisclosure(
            CONSUMER, DisclosureDeclaration(classes(derived=derived), self.repository)
        )

    def validate(self, now: datetime) -> None:
        parts = endpoint_parts(self.base_url)
        assert parts is not None
        # One application consumer covers both Agents and bounded rework.
        # The host independently repeats admission/currentness per invocation.
        declared = self.disclosure(derived=True)
        decision = evaluate_disclosure(
            DisclosureRequest(
                BINDING,
                self.provider.value,
                *parts,
                True,
                self.model,
                CONSUMER,
                "chat",
                declared.declaration,
                now,
            ),
            self.policy.admissions,
            self.policy.declarations,
        )
        if not decision.admitted:
            raise ValueError("remote disclosure policy does not admit this run")
        for admission in self.policy.admissions:
            if admission.not_after - admission.not_before > timedelta(hours=1):
                raise ValueError("remote admission lifetime exceeds one hour")


def load_profile(path: Path, *, synthetic: bool = False) -> RemoteProfile:
    """Strict, at most 16 KiB, non-secret TOML. Unknown fields fail closed."""
    with path.open("rb") as stream:
        raw = stream.read(16_385)
    if len(raw) > 16_384:
        raise ValueError("remote profile exceeds 16 KiB")
    data = tomllib.loads(raw.decode("utf-8"))
    required = {
        "provider",
        "base_url",
        "model",
        "repository",
        "revision",
        "processor",
        "locations",
        "retention_days",
        "training",
        "human_access",
        "subprocessors",
        "not_before",
        "not_after",
        "basis",
    }
    if set(data) != required or data["basis"] != "operator_attested":
        raise ValueError(
            "remote profile requires exactly the documented non-secret fields"
        )

    def text(key: str) -> str:
        value = data[key]
        if type(value) is not str or not 1 <= len(value) <= 256:
            raise ValueError("remote profile text is missing or oversized")
        return value

    def items(key: str) -> frozenset[str]:
        value = data[key]
        if (
            type(value) is not list
            or not 1 <= len(value) <= 16
            or any(type(v) is not str for v in value)
        ):
            raise ValueError("remote profile requires bounded string lists")
        return frozenset(value)

    parts = endpoint_parts(text("base_url"))
    if parts is None:
        raise ValueError("remote profile requires HTTPS")
    origin, root = parts
    basis = FactBasis.OPERATOR_ATTESTED
    days = data["retention_days"]
    if type(days) is not int:
        raise ValueError("retention_days must be an integer")
    retention = RetentionFact(RetentionKind.BOUNDED, days, basis)
    training = TrainingFact(TrainingUse(text("training")), basis)
    human = HumanAccessFact(HumanAccess(text("human_access")), basis)
    locations, subprocessors = items("locations"), items("subprocessors")
    declaration = ProcessorDeclaration(
        "forgeai-processor",
        text("revision"),
        text("provider"),
        origin,
        root,
        ProcessorIdentityFact(text("processor"), basis),
        LocationFact(locations, basis),
        retention,
        training,
        human,
        SubprocessorsFact(SubprocessorsKind.DECLARED, subprocessors, basis),
    )
    repository = RepositoryIdentity(text("repository"))
    admitted = (
        frozenset({DisclosureClass.SYNTHETIC}) if synthetic else classes(derived=True)
    )
    conditions = tuple(
        ClassConditions(
            c,
            locations,
            frozenset({retention.kind}),
            days,
            frozenset({training.value}),
            frozenset({human.value}),
            frozenset({SubprocessorsKind.DECLARED}),
        )
        for c in sorted(admitted - {DisclosureClass.SYNTHETIC}, key=lambda c: c.value)
    )
    times = tuple(data[key] for key in ("not_before", "not_after"))
    if any(type(t) is not datetime for t in times):
        raise ValueError("remote profile requires TOML offset datetimes")
    admissions = tuple(
        DisclosureAdmission(
            consumer,
            text("revision"),
            frozenset({BINDING}),
            text("provider"),
            origin,
            root,
            frozenset({text("model")}),
            consumer,
            frozenset({"chat"}),
            declaration.declaration_id,
            declaration.revision,
            admitted,
            conditions,
            frozenset() if synthetic else frozenset({repository}),
            times[0],
            times[1],
        )
        for consumer in (CONSUMER,)
    )
    return RemoteProfile(
        text("base_url"),
        text("model"),
        ProviderId(text("provider")),
        repository,
        RemoteDisclosureConfig((declaration,), admissions),
    )


def disclosure_preview(profile: RemoteProfile, task: TaskRequest) -> str:
    parts = endpoint_parts(profile.base_url)
    assert parts is not None
    lines = [
        "REMOTE disclosure (separate from mutation approval)",
        f"provider: {profile.provider.value}; model: {profile.model}",
        f"API origin: {parts[0]}; API root: {parts[1]}",
        f"task text and constraints: yes; task digest: {task_digest(task)}",
        "editable target contents: " + ", ".join(t.path.value for t in task.targets),
        "read-only context (Coding only): "
        + (", ".join(p.value for p in task.context) or "none"),
        "fixed platform instructions: yes",
        "rework diagnostics: possible only during one bounded rework",
        "Reviewer: task, changed files, proposal and check summaries (derived diagnostics)",
        "admitted application consumer: forgeai (Coding and Reviewer); purpose: chat",
    ]
    for admission in profile.policy.admissions:
        lines.append(
            f"admission: {admission.admission_id}/{admission.revision}; expires: {admission.not_after.isoformat()}"
        )
    return "\n".join(lines)


def role_disclosure_preview(
    role: str, profile: RemoteProfile, task: TaskRequest
) -> str:
    """Role-specific payload facts; reviewer never receives coder-only paths."""
    if role not in ("coder", "reviewer"):
        raise ValueError("unknown remote role")
    parts = endpoint_parts(profile.base_url)
    assert parts is not None
    lines = [
        f"REMOTE {role} disclosure (separate from mutation approval)",
        f"provider: {profile.provider.value}; model: {profile.model}",
        f"API origin: {parts[0]}; API root: {parts[1]}",
        f"task text and constraints: yes; task digest: {task_digest(task)}",
        "fixed platform instructions: yes",
    ]
    if role == "coder":
        lines += [
            "editable target contents: "
            + ", ".join(t.path.value for t in task.targets),
            "read-only context: "
            + (", ".join(p.value for p in task.context) or "none"),
            "rework diagnostics: possible only during one bounded rework",
        ]
    else:
        lines += [
            "changed-file contents, proposal rendering and check summaries (derived diagnostics)",
            "coder read-only context: not disclosed",
        ]
    lines += [
        f"admission: {a.admission_id}/{a.revision}; expires: {a.not_after.isoformat()}"
        for a in profile.policy.admissions
    ]
    return "\n".join(lines)
