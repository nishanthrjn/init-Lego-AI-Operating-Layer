"""F8a: Observation value construction, allowlist, and security tests.

CONTRACTS SS25/CTR-050; Gate-1 plan SS6/SS11. Observation is diagnostic
only -- these tests prove the bounded/closed-field contract, not general
data-loss prevention (F8a task SS37).
"""

from __future__ import annotations

import math
from dataclasses import FrozenInstanceError

import pytest

from legoai.kernel.errors import ErrorCategory
from legoai.kernel.identity import (
    ApplicationId,
    CorrelationId,
    OperationId,
    TenantId,
    TraceId,
)
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    OperationRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.observability.values import Observation, ObservationEventCode

SUPER_SECRET_CANARY_VALUE = "SUPER_SECRET_CANARY_VALUE"
AUTHORIZATION_CANARY = "AUTHORIZATION_CANARY"
PRIVATE_PAYLOAD_CANARY = "PRIVATE_PAYLOAD_CANARY"


def _target() -> ConfigurationRef:
    scope = ReferenceScope("owner1", TenantId("t1"))
    return ConfigurationRef(ApplicationRef(scope, ApplicationId("app1")), "i1")


def _operation() -> OperationRef:
    return OperationRef(_target(), OperationId("op1"), "observation-fixture")


class TestObservationEventCode:
    def test_valid_construction(self) -> None:
        code = ObservationEventCode("config.publish.committed")
        assert code.value == "config.publish.committed"

    def test_empty_rejected(self) -> None:
        with pytest.raises(ValueError):
            ObservationEventCode("")

    def test_wrong_type_rejected(self) -> None:
        with pytest.raises(TypeError):
            ObservationEventCode(123)  # type: ignore[arg-type]

    def test_frozen(self) -> None:
        code = ObservationEventCode("x")
        with pytest.raises(FrozenInstanceError):
            code.value = "y"  # type: ignore[misc]


class TestObservationConstruction:
    def test_minimal_valid_construction(self) -> None:
        obs = Observation(1, ObservationEventCode("x"), "owner")
        assert obs.schema_version == 1
        assert obs.event_code == ObservationEventCode("x")
        assert obs.owner == "owner"
        assert obs.correlation_id is None
        assert obs.error_category is None

    def test_full_valid_construction(self) -> None:
        target = _target()
        obs = Observation(
            schema_version=1,
            event_code=ObservationEventCode("config.publish.rejected"),
            owner="legoai.reference.application",
            correlation_id=CorrelationId("corr-1"),
            trace_id=TraceId("trace-1"),
            causation=_operation(),
            operation=_operation(),
            tenant_id=TenantId("t1"),
            configuration_revision=ConfigurationRevisionRef(
                target, "r1", Version(0, 1, 0)
            ),
            error_category=ErrorCategory.CONFLICT,
            safe_cause_reference="expected-revision-mismatch",
            latency_ms=12.5,
            size_bytes=256,
        )
        assert obs.latency_ms == 12.5
        assert obs.size_bytes == 256

    def test_immutable(self) -> None:
        obs = Observation(1, ObservationEventCode("x"), "owner")
        with pytest.raises(FrozenInstanceError):
            obs.owner = "other"  # type: ignore[misc]

    def test_unsupported_schema_version_rejected(self) -> None:
        with pytest.raises(ValueError):
            Observation(2, ObservationEventCode("x"), "owner")

    def test_schema_version_wrong_type_rejected(self) -> None:
        with pytest.raises(TypeError):
            Observation("1", ObservationEventCode("x"), "owner")  # type: ignore[arg-type]

    def test_bool_rejected_for_schema_version(self) -> None:
        with pytest.raises(TypeError):
            Observation(True, ObservationEventCode("x"), "owner")

    def test_event_code_wrong_type_rejected(self) -> None:
        with pytest.raises(TypeError):
            Observation(1, "not-a-code", "owner")  # type: ignore[arg-type]

    def test_owner_empty_rejected(self) -> None:
        with pytest.raises(ValueError):
            Observation(1, ObservationEventCode("x"), "")

    @pytest.mark.parametrize(
        "field_name,value",
        [
            ("correlation_id", "not-a-correlation-id"),
            ("trace_id", "not-a-trace-id"),
            ("causation", "not-an-operation-ref"),
            ("operation", "not-an-operation-ref"),
            ("tenant_id", "not-a-tenant-id"),
            ("configuration_revision", "not-a-revision-ref"),
            ("error_category", "not-a-category"),
        ],
    )
    def test_wrong_type_fields_rejected(self, field_name: str, value: object) -> None:
        with pytest.raises(TypeError):
            Observation(
                1,
                ObservationEventCode("x"),
                "owner",
                **{field_name: value},  # type: ignore[arg-type]
            )

    def test_safe_cause_reference_requires_error_category(self) -> None:
        with pytest.raises(ValueError):
            Observation(
                1,
                ObservationEventCode("x"),
                "owner",
                safe_cause_reference="some-cause",
            )

    def test_safe_cause_reference_with_error_category_ok(self) -> None:
        obs = Observation(
            1,
            ObservationEventCode("x"),
            "owner",
            error_category=ErrorCategory.VALIDATION_ERROR,
            safe_cause_reference="bad-input",
        )
        assert obs.safe_cause_reference == "bad-input"


class TestUnknownFieldRejection:
    def test_unsupported_field_rejected(self) -> None:
        with pytest.raises(TypeError):
            Observation(  # type: ignore[call-arg]
                1, ObservationEventCode("x"), "owner", password="x"
            )

    def test_prompt_field_rejected(self) -> None:
        with pytest.raises(TypeError):
            Observation(1, ObservationEventCode("x"), "owner", prompt="x")  # type: ignore[call-arg]

    def test_document_content_field_rejected(self) -> None:
        with pytest.raises(TypeError):
            Observation(  # type: ignore[call-arg]
                1, ObservationEventCode("x"), "owner", document_content="x"
            )

    def test_api_key_field_rejected(self) -> None:
        with pytest.raises(TypeError):
            Observation(1, ObservationEventCode("x"), "owner", api_key="x")  # type: ignore[call-arg]


class TestOversizeRejection:
    def test_oversize_owner_rejected(self) -> None:
        with pytest.raises(ValueError):
            Observation(1, ObservationEventCode("x"), "a" * 257)

    def test_oversize_event_code_rejected(self) -> None:
        with pytest.raises(ValueError):
            ObservationEventCode("a" * 257)

    def test_oversize_safe_cause_reference_rejected(self) -> None:
        with pytest.raises(ValueError):
            Observation(
                1,
                ObservationEventCode("x"),
                "owner",
                error_category=ErrorCategory.CONFLICT,
                safe_cause_reference="a" * 257,
            )


class TestNumericValidation:
    @pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
    def test_non_finite_latency_rejected(self, bad: float) -> None:
        with pytest.raises(ValueError):
            Observation(1, ObservationEventCode("x"), "owner", latency_ms=bad)

    def test_negative_latency_rejected(self) -> None:
        with pytest.raises(ValueError):
            Observation(1, ObservationEventCode("x"), "owner", latency_ms=-1.0)

    def test_negative_size_bytes_rejected(self) -> None:
        with pytest.raises(ValueError):
            Observation(1, ObservationEventCode("x"), "owner", size_bytes=-1)

    def test_int_rejected_for_latency_ms(self) -> None:
        with pytest.raises(TypeError):
            Observation(1, ObservationEventCode("x"), "owner", latency_ms=5)

    def test_bool_rejected_for_size_bytes(self) -> None:
        with pytest.raises(TypeError):
            Observation(1, ObservationEventCode("x"), "owner", size_bytes=True)


class TestNoArbitraryNesting:
    def test_nested_dict_rejected_as_cause_reference(self) -> None:
        with pytest.raises(TypeError):
            Observation(
                1,
                ObservationEventCode("x"),
                "owner",
                error_category=ErrorCategory.CONFLICT,
                safe_cause_reference={"nested": {"deep": "structure"}},  # type: ignore[arg-type]
            )

    def test_no_attributes_bag_exists(self) -> None:
        # The Gate-1 plan's own field list is closed/enumerated -- there is
        # no generic attributes/metadata mapping to smuggle nested data
        # through at all.
        obs = Observation(1, ObservationEventCode("x"), "owner")
        assert not hasattr(obs, "attributes")
        assert not hasattr(obs, "metadata")


class TestSensitiveDataCannotBeExpressed:
    """No field is wide enough to hold Secret/credential/payload content by
    construction, not merely by caller discipline (F8a task SS7-9)."""

    def test_canary_secret_rejected_via_unsupported_field(self) -> None:
        with pytest.raises(TypeError):
            Observation(  # type: ignore[call-arg]
                1,
                ObservationEventCode("x"),
                "owner",
                secret=SUPER_SECRET_CANARY_VALUE,
            )

    def test_canary_authorization_header_rejected_via_unsupported_field(self) -> None:
        with pytest.raises(TypeError):
            Observation(  # type: ignore[call-arg]
                1,
                ObservationEventCode("x"),
                "owner",
                authorization_header=AUTHORIZATION_CANARY,
            )

    def test_canary_private_payload_rejected_via_unsupported_field(self) -> None:
        with pytest.raises(TypeError):
            Observation(  # type: ignore[call-arg]
                1,
                ObservationEventCode("x"),
                "owner",
                private_payload=PRIVATE_PAYLOAD_CANARY,
            )

    def test_canary_values_do_not_appear_in_any_field_of_a_valid_observation(
        self,
    ) -> None:
        obs = Observation(
            1,
            ObservationEventCode("config.publish.rejected"),
            "owner",
            error_category=ErrorCategory.CONFLICT,
            safe_cause_reference="expected-revision-mismatch",
        )
        values = (
            obs.schema_version,
            obs.event_code.value,
            obs.owner,
            obs.safe_cause_reference,
            obs.error_category,
        )
        rendered = " ".join(str(v) for v in values)
        assert SUPER_SECRET_CANARY_VALUE not in rendered
        assert AUTHORIZATION_CANARY not in rendered
        assert PRIVATE_PAYLOAD_CANARY not in rendered
