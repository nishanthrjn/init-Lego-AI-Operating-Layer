"""MODEL-STRUCTURED-OUTPUT-1: provider-neutral structured-output values (ADR-022)."""

import dataclasses
import json

import pytest

from legoai.intelligence.model.values import (
    ChatMessage,
    ChatRequest,
    ChatRole,
    JsonArray,
    JsonObject,
    JsonString,
    StructuredOutputLimits,
    StructuredResponseFormat,
)

L = StructuredOutputLimits


def assessment_schema() -> JsonObject:
    """Shape of a current structured Agent result (a sufficiency assessment)."""
    request = JsonObject(
        (
            (
                "kind",
                JsonString(
                    enum=("named_evidence", "source_role", "operator_clarification")
                ),
            ),
            ("description", JsonString(max_length=1024)),
            ("path", JsonString(max_length=240, nullable=True)),
            ("choices", JsonArray(JsonString(max_length=256), max_items=8)),
        ),
        ("kind", "description", "path", "choices"),
    )
    return JsonObject(
        (
            (
                "disposition",
                JsonString(
                    enum=(
                        "sufficient",
                        "missing_governing_evidence",
                        "unresolved_ambiguity",
                    )
                ),
            ),
            ("explanation", JsonString(max_length=2048)),
            ("governing_sources", JsonArray(JsonString(max_length=240), max_items=8)),
            ("requests", JsonArray(request, max_items=8)),
        ),
        ("disposition", "explanation", "governing_sources", "requests"),
    )


def deep(depth: int) -> JsonObject:
    """`depth` levels in total, counting the root object and the string leaf."""
    node: JsonObject = JsonObject((("leaf", JsonString()),), ("leaf",))
    for _ in range(depth - 2):
        node = JsonObject((("child", node),), ("child",))
    return node


# 10-13 accepted shapes


def test_minimal_object_schema_accepted() -> None:
    fmt = StructuredResponseFormat(JsonObject((("answer", JsonString()),), ("answer",)))
    assert fmt.json_schema() == {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
        "additionalProperties": False,
    }


def test_required_enum_field_accepted() -> None:
    fmt = StructuredResponseFormat(
        JsonObject((("status", JsonString(enum=("ok", "fail"))),), ("status",))
    )
    status = fmt.json_schema()["properties"]["status"]  # type: ignore[index]
    assert status == {"type": "string", "enum": ["ok", "fail"]}


def test_nested_bounded_object_and_array_accepted() -> None:
    schema = StructuredResponseFormat(assessment_schema()).json_schema()
    requests = schema["properties"]["requests"]  # type: ignore[index]
    assert requests["type"] == "array" and requests["maxItems"] == 8
    item = requests["items"]
    assert item["additionalProperties"] is False
    assert item["properties"]["path"] == {"type": ["string", "null"], "maxLength": 240}


def test_nullable_enum_includes_null() -> None:
    node = JsonObject((("mode", JsonString(enum=("a", "b"), nullable=True)),))
    mode = StructuredResponseFormat(node).json_schema()["properties"]["mode"]  # type: ignore[index]
    assert mode == {"type": ["string", "null"], "enum": ["a", "b", None]}


# 14-21 rejected constructs and bounds


def test_unsupported_keyword_or_raw_dict_rejected() -> None:
    with pytest.raises(TypeError):
        StructuredResponseFormat({"type": "object", "$ref": "#/x"})  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        JsonString(pattern="x")  # type: ignore[call-arg]


def test_unsupported_type_rejected() -> None:
    with pytest.raises(TypeError):
        JsonObject((("n", 3),))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        JsonArray({"type": "integer"})  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        StructuredResponseFormat(JsonString())  # type: ignore[arg-type]


def test_remote_or_recursive_reference_impossible() -> None:
    # There is no reference node at all, and frozen values cannot form a cycle.
    assert {f.name for f in dataclasses.fields(JsonObject)} == {
        "properties",
        "required",
    }
    obj = JsonObject((("a", JsonString()),))
    with pytest.raises(dataclasses.FrozenInstanceError):
        obj.properties = (("a", obj),)  # type: ignore[misc]
    text = json.dumps(StructuredResponseFormat(assessment_schema()).json_schema())
    assert "$ref" not in text and "$defs" not in text


def test_excessive_depth_rejected() -> None:
    StructuredResponseFormat(deep(L.MAX_DEPTH))
    with pytest.raises(ValueError, match="deep"):
        StructuredResponseFormat(deep(L.MAX_DEPTH + 1))


def test_excessive_properties_rejected() -> None:
    props = tuple((f"p{i}", JsonString()) for i in range(L.MAX_PROPERTIES + 1))
    with pytest.raises(ValueError, match="properties"):
        JsonObject(props)


def test_excessive_enum_rejected() -> None:
    with pytest.raises(ValueError, match="enum"):
        JsonString(enum=tuple(f"v{i}" for i in range(L.MAX_ENUM_VALUES + 1)))
    with pytest.raises(ValueError):
        JsonString(enum=("x" * (L.MAX_ENUM_CHARS + 1),))


def test_excessive_nodes_or_serialized_size_rejected() -> None:
    wide = JsonObject(
        tuple(
            (f"g{i}", JsonObject(tuple((f"f{j}", JsonString()) for j in range(30))))
            for i in range(5)
        )
    )
    with pytest.raises(ValueError, match="nodes"):
        StructuredResponseFormat(wide)
    big = JsonObject(
        tuple(
            (f"k{i}", JsonString(enum=tuple(f"{'v' * 120}{j:02}" for j in range(8))))
            for i in range(20)
        )
    )
    with pytest.raises(ValueError, match="large"):
        StructuredResponseFormat(big)


def test_bounds_on_lengths_and_items() -> None:
    for bad in (0, -1, L.MAX_STRING_LENGTH + 1):
        with pytest.raises(ValueError):
            JsonString(max_length=bad)
    with pytest.raises(ValueError):
        JsonArray(JsonString(), max_items=L.MAX_ARRAY_ITEMS + 1)
    with pytest.raises(ValueError):
        JsonString(max_length=True)  # bool is not an int bound


# 22-25 determinism, immutability, names, enum duplicates


def test_deterministic_serialization_and_digest() -> None:
    a = StructuredResponseFormat(assessment_schema())
    b = StructuredResponseFormat(assessment_schema())
    assert a == b and a.digest() == b.digest() and len(a.digest()) == 64
    assert json.dumps(a.json_schema(), sort_keys=True) == json.dumps(
        b.json_schema(), sort_keys=True
    )
    other = StructuredResponseFormat(JsonObject((("x", JsonString()),)))
    assert other.digest() != a.digest()


def test_immutable_values_and_fresh_copies() -> None:
    fmt = StructuredResponseFormat(assessment_schema())
    first = fmt.json_schema()
    first["properties"]["disposition"]["enum"].append("hacked")  # type: ignore[index]
    first["type"] = "string"
    assert fmt.json_schema()["type"] == "object"
    assert "hacked" not in json.dumps(fmt.json_schema())
    with pytest.raises(dataclasses.FrozenInstanceError):
        fmt.schema = JsonObject((("y", JsonString()),))  # type: ignore[misc]


@pytest.mark.parametrize(
    "name", ["", "Upper", "has-dash", "1start", "x" * 65, "sp ace"]
)
def test_invalid_property_name_rejected(name: str) -> None:
    with pytest.raises(ValueError):
        JsonObject(((name, JsonString()),))


def test_invalid_required_name_rejected() -> None:
    with pytest.raises(ValueError, match="required"):
        JsonObject((("a", JsonString()),), ("b",))
    with pytest.raises(ValueError, match="required"):
        JsonObject((("a", JsonString()),), ("a", "a"))


def test_duplicate_enum_or_property_rejected_deterministically() -> None:
    with pytest.raises(ValueError, match="duplicate enum"):
        JsonString(enum=("a", "a"))
    with pytest.raises(ValueError, match="duplicate property"):
        JsonObject((("a", JsonString()), ("a", JsonString())))


# 26 backward compatibility of ChatRequest


def test_ordinary_chat_request_unchanged() -> None:
    request = ChatRequest((ChatMessage(ChatRole.USER, "hi"),))
    assert request.response_format is None
    assert ChatRequest((ChatMessage(ChatRole.USER, "hi"),)) == request
    fields = [f.name for f in dataclasses.fields(ChatRequest)]
    assert fields == ["messages", "response_format"]


def test_response_format_type_checked() -> None:
    with pytest.raises(TypeError):
        ChatRequest(
            (ChatMessage(ChatRole.USER, "hi"),),
            {"type": "json_schema"},  # type: ignore[arg-type]
        )
    fmt = StructuredResponseFormat(assessment_schema())
    assert ChatRequest((ChatMessage(ChatRole.USER, "hi"),), fmt).response_format is fmt
