"""Validate this experiment's fixed JSON-schema subset without fetching schemas."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from .contracts import Rejected


def validate_result(value: dict[str, Any]) -> None:
    schema = json.loads(
        (Path(__file__).parent / "result.schema.json").read_text(encoding="utf-8")
    )
    _validate(value, schema, schema)


def _validate(value: Any, rule: dict[str, Any], document: dict[str, Any]) -> None:
    if "$ref" in rule:
        reference = rule["$ref"]
        if not reference.startswith("#/$defs/"):
            raise Rejected("RESULT_SCHEMA_INVALID")
        _validate(
            value, document["$defs"][reference.removeprefix("#/$defs/")], document
        )
        return
    types = {
        "object": type(value) is dict,
        "array": type(value) is list,
        "string": type(value) is str,
        "integer": type(value) is int,
        "number": type(value) in (int, float),
        "boolean": type(value) is bool,
        "null": value is None,
    }
    expected = rule.get("type", list(types))
    expected = [expected] if isinstance(expected, str) else expected
    valid = any(types[name] for name in expected)
    if "const" in rule:
        valid = valid and value == rule["const"]
    if "enum" in rule:
        valid = valid and value in rule["enum"]
    if not valid:
        raise Rejected("RESULT_SCHEMA_INVALID")
    if isinstance(value, dict):
        properties = rule.get("properties", {})
        if not set(rule.get("required", [])) <= set(value):
            raise Rejected("RESULT_SCHEMA_INVALID")
        if (
            rule.get("additionalProperties") is False
            and not set(value) <= properties.keys()
        ):
            raise Rejected("RESULT_SCHEMA_INVALID")
        for key, item in value.items():
            if key in properties:
                _validate(item, properties[key], document)
    elif isinstance(value, list):
        if len(value) > rule.get("maxItems", len(value)):
            raise Rejected("RESULT_SCHEMA_INVALID")
        for item in value:
            _validate(item, rule.get("items", {}), document)
    elif isinstance(value, str):
        if len(value) > rule.get("maxLength", len(value)):
            raise Rejected("RESULT_SCHEMA_INVALID")
        if "pattern" in rule and re.fullmatch(rule["pattern"], value) is None:
            raise Rejected("RESULT_SCHEMA_INVALID")
    elif type(value) in (int, float):
        if not math.isfinite(value):
            raise Rejected("RESULT_SCHEMA_INVALID")
        if value < rule.get("minimum", value) or value > rule.get("maximum", value):
            raise Rejected("RESULT_SCHEMA_INVALID")
