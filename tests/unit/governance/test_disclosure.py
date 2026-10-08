"""ADR-024 REMOTE-DISCLOSURE-GOVERNANCE-1: `model-disclosure/1` values and the
pure admission evaluator. Values are immutable records; the evaluator is a
deterministic decision over explicit inputs and grants nothing by itself.
"""

import ast
import dataclasses
import inspect
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest

import legoai.governance.disclosure as disclosure
from legoai.governance.disclosure import (
    ClassConditions,
    DisclosureAdmission,
    DisclosureClass,
    DisclosureDecision,
    DisclosureDeclaration,
    DisclosureRefusal,
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
    SourceReference,
    SubprocessorsFact,
    SubprocessorsKind,
    TrainingFact,
    TrainingUse,
    endpoint_parts,
    evaluate_disclosure,
    vocabulary,
)

NOW = datetime(2026, 10, 9, 12, tzinfo=UTC)
DAY = timedelta(days=1)
ORIGIN = "https://models.example.org"
ROOT = "/v1"
SOURCE = SourceReference("Provider data-use terms", date(2026, 10, 1))
REPO = RepositoryIdentity("repo-a")
OTHER_REPO = RepositoryIdentity("repo-b")
ALL = frozenset(DisclosureClass)
REAL = ALL - {DisclosureClass.SYNTHETIC}
DECLARED = FactBasis.PROVIDER_DECLARED
ATTESTED = FactBasis.OPERATOR_ATTESTED
UNKNOWN = FactBasis.UNKNOWN


def declaration(**changes: Any) -> ProcessorDeclaration:
    value = ProcessorDeclaration(
        "processor",
        "r1",
        "remote-endpoint",
        ORIGIN,
        ROOT,
        ProcessorIdentityFact("Example Processing GmbH", DECLARED, SOURCE),
        LocationFact(frozenset({"DE"}), DECLARED, SOURCE),
        RetentionFact(RetentionKind.BOUNDED, 30, DECLARED, SOURCE),
        TrainingFact(TrainingUse.NO, DECLARED, SOURCE),
        HumanAccessFact(HumanAccess.RESTRICTED, DECLARED, SOURCE),
        SubprocessorsFact(SubprocessorsKind.NOT_MATERIAL, frozenset(), ATTESTED),
    )
    return replace(value, **changes)


def unknown_facts() -> dict[str, object]:
    return {
        "location": LocationFact(None, UNKNOWN),
        "retention": RetentionFact(RetentionKind.UNKNOWN, None, UNKNOWN),
        "training": TrainingFact(TrainingUse.UNKNOWN, UNKNOWN),
        "human_access": HumanAccessFact(HumanAccess.UNKNOWN, UNKNOWN),
        "subprocessors": SubprocessorsFact(
            SubprocessorsKind.UNKNOWN, frozenset(), UNKNOWN
        ),
    }


def conditions(disclosure_class: DisclosureClass, **changes: Any) -> ClassConditions:
    value = ClassConditions(
        disclosure_class,
        frozenset({"DE", "EU"}),
        frozenset({RetentionKind.NONE, RetentionKind.BOUNDED}),
        30,
        frozenset({TrainingUse.NO, TrainingUse.NO_BY_CONFIGURATION}),
        frozenset({HumanAccess.NONE, HumanAccess.RESTRICTED}),
        frozenset({SubprocessorsKind.DECLARED, SubprocessorsKind.NOT_MATERIAL}),
    )
    return replace(value, **changes)


def admission(
    classes: frozenset[DisclosureClass] = ALL, **changes: Any
) -> DisclosureAdmission:
    repository = classes & {
        DisclosureClass.REPOSITORY_CONTENT,
        DisclosureClass.DERIVED_DIAGNOSTIC,
    }
    value = DisclosureAdmission(
        "admission",
        "a1",
        frozenset({"remote"}),
        "remote-endpoint",
        ORIGIN,
        ROOT,
        frozenset({"model-a"}),
        "forgeai",
        frozenset({"chat"}),
        "processor",
        "r1",
        classes,
        tuple(
            conditions(c)
            for c in sorted(
                classes - {DisclosureClass.SYNTHETIC}, key=lambda c: c.value
            )
        ),
        frozenset({REPO}) if repository else frozenset(),
        NOW - DAY,
        NOW + DAY,
    )
    return replace(value, **changes)


def request(
    classes: frozenset[DisclosureClass] = ALL, **changes: Any
) -> DisclosureRequest:
    repository = classes & {
        DisclosureClass.REPOSITORY_CONTENT,
        DisclosureClass.DERIVED_DIAGNOSTIC,
    }
    value = DisclosureRequest(
        "remote",
        "remote-endpoint",
        ORIGIN,
        ROOT,
        True,
        "model-a",
        "forgeai",
        "chat",
        DisclosureDeclaration(classes, REPO if repository else None),
        NOW,
    )
    return replace(value, **changes)


def decide(
    req: DisclosureRequest,
    adm: DisclosureAdmission | None = None,
    dec: ProcessorDeclaration | None = None,
) -> DisclosureDecision:
    return evaluate_disclosure(req, (adm or admission(),), (dec or declaration(),))


# Vocabulary and basis


def test_vocabulary_is_exactly_model_disclosure_1() -> None:
    assert vocabulary() == "model-disclosure/1"
    assert {c.name for c in DisclosureClass} == {
        "SYNTHETIC",
        "PLATFORM_INSTRUCTION",
        "TASK_TEXT",
        "REPOSITORY_CONTENT",
        "DERIVED_DIAGNOSTIC",
    }
    assert {b.name for b in FactBasis} == {
        "VERIFIED",
        "PROVIDER_DECLARED",
        "OPERATOR_ATTESTED",
        "UNKNOWN",
    }
    # No sensitivity/DLP vocabulary and no content inspection exists.
    names = set(vars(disclosure))
    for word in ("SECRET", "CONFIDENTIAL", "PII", "INTERNAL", "PUBLIC"):
        assert word not in {c.name for c in DisclosureClass}
    assert not {n for n in names if "inspect" in n.lower() or "scan" in n.lower()}


def test_declared_facts_cannot_claim_mechanical_verification() -> None:
    with pytest.raises(ValueError):
        TrainingFact(TrainingUse.NO, FactBasis.VERIFIED, SOURCE)
    with pytest.raises(ValueError):  # a policy URL is a source, not verification
        LocationFact(frozenset({"DE"}), FactBasis.VERIFIED, SOURCE)


@pytest.mark.parametrize(
    "build",
    [
        lambda: TrainingFact(TrainingUse.NO, UNKNOWN),  # known value, unknown basis
        lambda: TrainingFact(TrainingUse.UNKNOWN, DECLARED, SOURCE),
        lambda: TrainingFact(TrainingUse.NO, DECLARED),  # declared needs source
        lambda: TrainingFact(TrainingUse.UNKNOWN, UNKNOWN, SOURCE),
        lambda: TrainingFact(TrainingUse.NO_BY_CONFIGURATION, DECLARED, SOURCE),
        lambda: SubprocessorsFact(
            SubprocessorsKind.NOT_MATERIAL, frozenset(), DECLARED, SOURCE
        ),
        lambda: SubprocessorsFact(SubprocessorsKind.DECLARED, frozenset(), ATTESTED),
        lambda: SubprocessorsFact(SubprocessorsKind.UNKNOWN, frozenset({"x"}), UNKNOWN),
        lambda: RetentionFact(RetentionKind.BOUNDED, None, DECLARED, SOURCE),
        lambda: RetentionFact(RetentionKind.NONE, 3, DECLARED, SOURCE),
        lambda: RetentionFact(RetentionKind.BOUNDED, -1, DECLARED, SOURCE),
        lambda: SourceReference("x" * 513, date(2026, 1, 1)),
        lambda: SourceReference("line\nbreak", date(2026, 1, 1)),
        lambda: LocationFact(frozenset(), DECLARED, SOURCE),
        lambda: LocationFact(frozenset({"*"}), DECLARED, SOURCE),
    ],
)
def test_fact_basis_rules(build: object) -> None:
    with pytest.raises((ValueError, TypeError)):
        build()  # type: ignore[operator]


def test_source_reference_is_bounded_and_hidden_from_repr() -> None:
    reference = SourceReference("https://provider.example/terms", date(2026, 10, 1))
    assert "provider.example" not in repr(reference)
    assert "Example Processing" not in repr(declaration())


# Values: immutability, exactness, no defaults


def test_values_are_immutable() -> None:
    for value in (declaration(), admission(), request(), REPO):
        with pytest.raises(FrozenInstanceError):
            value.revision = "changed"  # type: ignore[misc,union-attr]
        assert not hasattr(value, "__dict__")


def test_no_default_admission_exists() -> None:
    parameters = inspect.signature(DisclosureAdmission).parameters
    assert all(p.default is inspect.Parameter.empty for p in parameters.values())
    assert decide(request(), adm=admission(bindings=frozenset({"other"}))).refusal is (
        DisclosureRefusal.NO_ADMISSION
    )
    assert evaluate_disclosure(request(), (), (declaration(),)).refusal is (
        DisclosureRefusal.NO_ADMISSION
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"models": frozenset({"*"})},
        {"models": frozenset({"model-*"})},
        {"models": frozenset()},
        {"bindings": frozenset({"*"})},
        {"repositories": frozenset({RepositoryIdentity("repo-a"), REPO})}
        | {"models": frozenset({"model?"})},
        {"not_after": NOW - 2 * DAY},
        {"not_after": NOW - DAY},
        {"not_before": NOW.replace(tzinfo=None)},
        {"endpoint_origin": "http://models.example.org"},
        {"endpoint_origin": "https://Models.example.org"},
        {"endpoint_origin": "https://models.example.org:443"},
        {"api_root": "/v1/"},
        {"purposes": frozenset()},
        {"consumer": " forgeai"},
    ],
)
def test_admission_shape_is_exact(changes: dict[str, Any]) -> None:
    with pytest.raises((ValueError, TypeError)):
        admission(**changes)


def test_no_wildcard_repository() -> None:
    for value in ("*", "repo-*", "repo?"):
        with pytest.raises(ValueError):
            RepositoryIdentity(value)


def test_repositories_are_named_exactly_for_repository_classes() -> None:
    with pytest.raises(ValueError):
        admission(repositories=frozenset())
    with pytest.raises(ValueError):
        admission(
            frozenset({DisclosureClass.SYNTHETIC}), repositories=frozenset({REPO})
        )
    with pytest.raises(ValueError):
        DisclosureDeclaration(frozenset({DisclosureClass.TASK_TEXT}), REPO)
    with pytest.raises(ValueError):
        DisclosureDeclaration(frozenset({DisclosureClass.REPOSITORY_CONTENT}))


def test_conditions_only_tighten() -> None:
    with pytest.raises(ValueError):
        conditions(DisclosureClass.TASK_TEXT, training=frozenset({TrainingUse.UNKNOWN}))
    with pytest.raises(ValueError):
        conditions(
            DisclosureClass.TASK_TEXT,
            retention=frozenset({RetentionKind.UNKNOWN}),
            max_retention_days=None,
        )
    with pytest.raises(ValueError):
        conditions(DisclosureClass.REPOSITORY_CONTENT, subprocessors=None)
    with pytest.raises(ValueError):
        conditions(DisclosureClass.SYNTHETIC)
    with pytest.raises(ValueError):  # bound stated exactly when BOUNDED accepted
        conditions(DisclosureClass.TASK_TEXT, retention=frozenset({RetentionKind.NONE}))
    conditions(DisclosureClass.TASK_TEXT, subprocessors=None)


def test_admission_requires_one_condition_set_per_real_class() -> None:
    with pytest.raises(ValueError):
        admission(conditions=())
    with pytest.raises(ValueError):
        admission(
            frozenset({DisclosureClass.TASK_TEXT}),
            conditions=(
                conditions(DisclosureClass.TASK_TEXT),
                conditions(DisclosureClass.TASK_TEXT),
            ),
        )


def test_derived_diagnostic_requires_repository_content_in_admission() -> None:
    with pytest.raises(ValueError):
        admission(
            frozenset({DisclosureClass.DERIVED_DIAGNOSTIC, DisclosureClass.TASK_TEXT})
        )


def test_endpoint_parts_normalize_https_only() -> None:
    assert endpoint_parts("https://Models.Example.org/v1/") == (ORIGIN, "/v1")
    assert endpoint_parts("https://models.example.org:8443/api/v1") == (
        "https://models.example.org:8443",
        "/api/v1",
    )
    assert endpoint_parts("https://models.example.org") == (ORIGIN, "/")
    for url in (
        "http://models.example.org/v1",
        "https://u:p@models.example.org/v1",
        "https://models.example.org/v1?x=1",
        "https://models.example.org/v1#f",
        "https://models.example.org:bad/v1",
        "https://models.example.org//v1",
    ):
        assert endpoint_parts(url) is None, url


# Pure evaluation


def test_admitted_when_everything_matches() -> None:
    decision = decide(request())
    assert decision.admitted and decision.refusal is None
    assert (decision.admission_id, decision.declaration_revision) == ("admission", "r1")


@pytest.mark.parametrize(
    ("changes", "refusal"),
    [
        ({"at": NOW - 2 * DAY}, DisclosureRefusal.NOT_YET_VALID),
        ({"at": NOW + DAY}, DisclosureRefusal.EXPIRED),
        ({"at": NOW + 2 * DAY}, DisclosureRefusal.EXPIRED),
        ({"provider_id": "other"}, DisclosureRefusal.PROVIDER_MISMATCH),
        (
            {"endpoint_origin": "https://elsewhere.example.org"},
            DisclosureRefusal.ENDPOINT_MISMATCH,
        ),
        ({"api_root": "/v2"}, DisclosureRefusal.API_ROOT_MISMATCH),
        ({"remote": False}, DisclosureRefusal.DEPLOYMENT_MISMATCH),
        ({"model": "model-b"}, DisclosureRefusal.MODEL_NOT_ADMITTED),
        ({"model": "*"}, DisclosureRefusal.MODEL_NOT_ADMITTED),
        ({"consumer": "other-app"}, DisclosureRefusal.CONSUMER_MISMATCH),
        ({"purpose": "embedding"}, DisclosureRefusal.PURPOSE_MISMATCH),
        ({"binding_id": "unadmitted"}, DisclosureRefusal.NO_ADMISSION),
    ],
)
def test_each_mismatch_refuses(
    changes: dict[str, Any], refusal: DisclosureRefusal
) -> None:
    assert decide(request(**changes)).refusal is refusal


def test_unclassified_is_never_admitted() -> None:
    unclassified = request(declaration=DisclosureDeclaration(frozenset()))
    assert unclassified.declaration.unclassified
    assert decide(unclassified).refusal is DisclosureRefusal.UNCLASSIFIED


def test_unadmitted_class_refuses_and_content_cannot_widen() -> None:
    narrow = admission(
        frozenset({DisclosureClass.SYNTHETIC, DisclosureClass.TASK_TEXT})
    )
    # A declaration naming more classes than admitted never widens the admission.
    assert decide(request(), adm=narrow).refusal is DisclosureRefusal.CLASS_NOT_ADMITTED
    task_only = request(frozenset({DisclosureClass.TASK_TEXT}))
    assert decide(task_only, adm=narrow).admitted


def test_unadmitted_repository_refuses() -> None:
    wrong = request(
        declaration=DisclosureDeclaration(
            frozenset({DisclosureClass.REPOSITORY_CONTENT}), OTHER_REPO
        )
    )
    assert decide(wrong).refusal is DisclosureRefusal.REPOSITORY_NOT_ADMITTED


def test_derived_diagnostic_lineage_is_enforced() -> None:
    derived = DisclosureDeclaration(
        frozenset({DisclosureClass.DERIVED_DIAGNOSTIC}), REPO
    )
    # Admitted: REPOSITORY_CONTENT is admitted for the same repository.
    assert decide(request(declaration=derived)).admitted
    # Different repository: refused even though the class is admitted.
    other = DisclosureDeclaration(
        frozenset({DisclosureClass.DERIVED_DIAGNOSTIC}), OTHER_REPO
    )
    assert decide(request(declaration=other)).refusal is (
        DisclosureRefusal.REPOSITORY_NOT_ADMITTED
    )
    # The evaluator re-checks lineage even against a malformed admission value.
    forged = admission()
    object.__setattr__(
        forged, "classes", frozenset({DisclosureClass.DERIVED_DIAGNOSTIC})
    )
    assert decide(request(declaration=derived), adm=forged).refusal is (
        DisclosureRefusal.CLASS_NOT_ADMITTED
    )


def test_changed_declaration_revision_invalidates_admission() -> None:
    assert decide(request(), dec=declaration(revision="r2")).refusal is (
        DisclosureRefusal.DECLARATION_STALE
    )
    assert evaluate_disclosure(request(), (admission(),), ()).refusal is (
        DisclosureRefusal.DECLARATION_STALE
    )


@pytest.mark.parametrize("fact", sorted(unknown_facts()))
@pytest.mark.parametrize(
    "classes",
    [
        frozenset({DisclosureClass.REPOSITORY_CONTENT}),
        frozenset({DisclosureClass.DERIVED_DIAGNOSTIC}),
        frozenset({DisclosureClass.TASK_TEXT}),
        frozenset({DisclosureClass.PLATFORM_INSTRUCTION}),
        frozenset({DisclosureClass.SYNTHETIC, DisclosureClass.TASK_TEXT}),
    ],
    ids=["repo", "derived", "task", "platform", "synthetic+task"],
)
def test_unknown_mandatory_fact_refuses_for_real_content(
    fact: str, classes: frozenset[DisclosureClass]
) -> None:
    dec = declaration(**{fact: unknown_facts()[fact]})
    repository = classes & {
        DisclosureClass.REPOSITORY_CONTENT,
        DisclosureClass.DERIVED_DIAGNOSTIC,
    }
    req = request(
        declaration=DisclosureDeclaration(classes, REPO if repository else None)
    )
    decision = decide(req, dec=dec)
    if fact == "subprocessors" and not repository:
        # ADR-024 §5.2: subprocessors are mandatory only for repository
        # classes. Not mandatory, so not REQUIRED_FACT_UNKNOWN; this admission
        # tightened it with explicit conditions, so it is an unmet condition.
        assert decision.refusal is DisclosureRefusal.CONDITION_UNMET
        loose = admission(
            conditions=tuple(
                conditions(
                    c,
                    subprocessors=None
                    if c
                    in {DisclosureClass.TASK_TEXT, DisclosureClass.PLATFORM_INSTRUCTION}
                    else frozenset({SubprocessorsKind.NOT_MATERIAL}),
                )
                for c in sorted(REAL, key=lambda c: c.value)
            )
        )
        assert decide(req, adm=loose, dec=dec).admitted
    else:
        assert decision.refusal is DisclosureRefusal.REQUIRED_FACT_UNKNOWN


def test_synthetic_permits_the_allowed_unknown_facts() -> None:
    probe = admission(frozenset({DisclosureClass.SYNTHETIC}))
    unknown = declaration(**unknown_facts())
    synthetic = request(frozenset({DisclosureClass.SYNTHETIC}))
    assert decide(synthetic, adm=probe, dec=unknown).admitted
    # Provider identity stays mandatory even for SYNTHETIC.
    anonymous = replace(unknown, processor=ProcessorIdentityFact(None, UNKNOWN))
    assert decide(synthetic, adm=probe, dec=anonymous).refusal is (
        DisclosureRefusal.REQUIRED_FACT_UNKNOWN
    )
    # The probe admission never covers real content.
    assert (
        decide(
            request(frozenset({DisclosureClass.TASK_TEXT})), adm=probe, dec=unknown
        ).refusal
        is DisclosureRefusal.CLASS_NOT_ADMITTED
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"location": LocationFact(frozenset({"US"}), DECLARED, SOURCE)},
        {"location": LocationFact(frozenset({"DE", "US"}), DECLARED, SOURCE)},
        {"retention": RetentionFact(RetentionKind.UNBOUNDED, None, DECLARED, SOURCE)},
        {"retention": RetentionFact(RetentionKind.BOUNDED, 31, DECLARED, SOURCE)},
        {"training": TrainingFact(TrainingUse.YES, DECLARED, SOURCE)},
        {"human_access": HumanAccessFact(HumanAccess.YES, DECLARED, SOURCE)},
        {
            "subprocessors": SubprocessorsFact(
                SubprocessorsKind.DECLARED, frozenset({"Cloud Inc"}), DECLARED, SOURCE
            )
        },
    ],
    ids=[
        "location",
        "partial-location",
        "retention",
        "retention-bound",
        "training",
        "human",
        "subprocessors",
    ],
)
def test_unacceptable_condition_refuses(changes: dict[str, Any]) -> None:
    if "subprocessors" in changes:
        adm = admission(
            conditions=tuple(
                conditions(
                    c,
                    subprocessors=frozenset({SubprocessorsKind.NOT_MATERIAL}),
                )
                for c in sorted(REAL, key=lambda c: c.value)
            )
        )
    else:
        adm = admission()
    assert decide(request(), adm=adm, dec=declaration(**changes)).refusal is (
        DisclosureRefusal.CONDITION_UNMET
    )


def test_ambiguous_admissions_refuse_rather_than_choose() -> None:
    twin = replace(admission(), admission_id="twin")
    assert (
        evaluate_disclosure(request(), (admission(), twin), (declaration(),)).refusal
        is DisclosureRefusal.NO_ADMISSION
    )


def test_evaluator_is_pure_and_deterministic() -> None:
    adm, dec, req = admission(), declaration(), request()
    first = evaluate_disclosure(req, (adm,), (dec,))
    assert all(evaluate_disclosure(req, (adm,), (dec,)) == first for _ in range(5))
    assert (adm, dec, req) == (admission(), declaration(), request())
    tree = ast.parse(inspect.getsource(disclosure))
    imported: set[str] = set()
    for node in ast.walk(tree):
        assert not isinstance(node, (ast.Global, ast.Nonlocal)), "mutable state"
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"open", "eval", "exec"}, node.func.id
    # urllib.parse is pure string parsing; nothing opens files, sockets or env.
    assert imported <= {
        "urllib.parse",
        "dataclasses",
        "datetime",
        "enum",
        "legoai.kernel.identity",
    }, imported


def test_refusal_taxonomy_is_closed() -> None:
    assert {r.value for r in DisclosureRefusal} == {
        "no_admission",
        "not_yet_valid",
        "expired",
        "provider_mismatch",
        "endpoint_mismatch",
        "api_root_mismatch",
        "deployment_mismatch",
        "model_not_admitted",
        "consumer_mismatch",
        "purpose_mismatch",
        "unclassified",
        "class_not_admitted",
        "repository_not_admitted",
        "declaration_stale",
        "required_fact_unknown",
        "condition_unmet",
    }


def test_admitted_decision_must_name_its_admission() -> None:
    with pytest.raises(ValueError):
        DisclosureDecision(None)
    assert {f.name for f in dataclasses.fields(DisclosureDecision)} == {
        "refusal",
        "admission_id",
        "admission_revision",
        "declaration_revision",
    }
