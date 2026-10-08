"""MODEL-STRUCTURED-OUTPUT-1-LIVE-PROBE: one synthetic ADR-022 call to local Ollama.

Provider-compatibility evidence only. Public Core imports only; the call goes
through the governed local host (route -> capable Ollama binding -> adapter).
Metadata preflight first; exactly one chat call; no retry, repair or fallback.
Persists bounded, normalized evidence; never the prompt text or raw reply.
"""

import argparse
import asyncio
import hashlib
import json
import platform
import subprocess
import time
import urllib.request
import uuid
from datetime import UTC, datetime, timedelta
from http.client import HTTPConnection
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener

from legoai.governance.values import GrantId, PolicyRef
from legoai.intelligence.model.routing import ModelRequirement
from legoai.intelligence.model.values import (
    ChatMessage,
    ChatRequest,
    ChatRole,
    JsonArray,
    JsonObject,
    JsonString,
    ProviderId,
    StructuredResponseFormat,
)
from legoai.kernel.identity import ApplicationId, PrincipalId, TenantId
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.runtime.api import (
    LocalHostConfig,
    ModelBindingConfig,
    ModelPurpose,
    OllamaSettings,
    OperatorGrant,
)
from legoai.runtime.local import open_local_host

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PROBE = "model-structured-output-1-live-probe/1"
APPROVAL = (
    "Maintainer authorization 2026-10-08: MODEL-STRUCTURED-OUTPUT-1-LIVE-PROBE "
    "(metadata identity checks + exactly one synthetic structured-output call)"
)
URL = "http://127.0.0.1:11434"
VERSION = "0.40.0"  # exact pin
MODEL = "qwen2.5-coder:14b"
MODEL_DIGEST = "sha256:9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849"
TIMEOUT_SECONDS = 600.0  # existing qualified per-call bound; never raised
IMPLEMENTATION = "f3d824d"
ACCEPTANCE = "d9645d0"
UNCHANGED_SINCE = "3916451"
UNCHANGED_PATHS = (
    "packages/legoai-engineering/src/legoai_engineering/analyst/request_policy.py",
    "examples/forgeai/evaluation/analyst_evidence_loop",
    "examples/forgeai/evaluation/analyst_sufficiency_hardening_h1",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_eval2",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_eval3",
)

STATUS = ("alpha", "beta")
LABEL_MAX = 8
ITEMS_MAX = 2
ITEM_MAX_LENGTH = 3
NOTE = ("n/a",)  # plus null
FIELDS = ("status", "label", "items", "note")
# Deliberately conflicts with every constraint; synthetic, no domain content.
PROMPT = (
    "Return a JSON object with exactly these values: "
    '"status": "gamma", '
    '"label": "this label is far longer than eight characters", '
    '"items": ["aaaaaa", "bbbbbb", "cccccc", "dddddd", "eeeeee"], '
    '"note": "free text instead of the allowed value", '
    'and also an extra property "extra": "yes".'
)


def response_format() -> StructuredResponseFormat:
    return StructuredResponseFormat(
        JsonObject(
            (
                ("status", JsonString(enum=STATUS)),
                ("label", JsonString(max_length=LABEL_MAX)),
                (
                    "items",
                    JsonArray(
                        JsonString(max_length=ITEM_MAX_LENGTH), max_items=ITEMS_MAX
                    ),
                ),
                ("note", JsonString(enum=NOTE, nullable=True)),
            ),
            FIELDS,
        )
    )


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True, timeout=10
    ).stdout.strip()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def repository_preconditions() -> dict[str, Any]:
    if git("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("TRACKED_TREE_DIRTY")
    head = git("rev-parse", "HEAD")
    for commit in (IMPLEMENTATION, ACCEPTANCE, UNCHANGED_SINCE):
        git("merge-base", "--is-ancestor", commit, "HEAD")  # raises if absent
    if (
        not git("show", "HEAD:adrs/ADR-022.md")
        .splitlines()[2]
        .startswith("Status: Accepted")
    ):
        raise ValueError("ADR_022_ACCEPTANCE_NOT_COMMITTED")
    # Path-level diff only; no fixture, oracle or scorer content is read.
    if git("diff", "--name-only", UNCHANGED_SINCE, "HEAD", "--", *UNCHANGED_PATHS):
        raise ValueError("H1_OR_SAFETY_EVAL_CHANGED")
    probe = Path(__file__).resolve()
    return {
        "git_head": head,
        "clean_tracked_tree": True,
        "implementation_commit": IMPLEMENTATION,
        "adr_022_acceptance_commit": ACCEPTANCE,
        "h1_and_safety_eval_2_3_unchanged_since": UNCHANGED_SINCE,
        "probe_source": probe.relative_to(ROOT).as_posix(),
        "probe_source_sha256": sha256(probe.read_bytes().replace(b"\r\n", b"\n")),
        "probe_source_tracked": bool(
            git("ls-files", "--", probe.relative_to(ROOT).as_posix())
        ),
    }


def metadata_probe() -> tuple[str, str, str]:
    """GET /api/version and /api/tags only; no inference, no model load."""
    parts = urlsplit(URL)
    if (
        parts.hostname != "127.0.0.1"
        or parts.username is not None
        or parts.password is not None
        or parts.query
        or parts.port is None
    ):
        raise ValueError("LOCAL_CREDENTIAL_FREE_ENDPOINT_REQUIRED")
    objects = []
    for path in ("/api/version", "/api/tags"):
        connection = HTTPConnection(parts.hostname, parts.port, timeout=5)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            if response.status != 200:
                raise ValueError("PROVIDER_METADATA_STATUS")
            body = response.read(1048577)
            if len(body) > 1048576:
                raise ValueError("PROVIDER_METADATA_BOUND")
            objects.append(json.loads(body))
        finally:
            connection.close()
    version, tags = objects
    rows = [m for m in tags["models"] if m["name"] == MODEL]
    if len(rows) != 1:
        raise ValueError("MODEL_TAG_NOT_EXACTLY_ONE")
    return version["version"], rows[0]["name"], "sha256:" + rows[0]["digest"]


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        raise ValueError("REDIRECT_FORBIDDEN")


class WireObserver:
    """Pass-through around urlopen: records request shape, never messages."""

    def __init__(self, expected_format: dict[str, Any]) -> None:
        self.expected_format = expected_format
        self.original = urllib.request.urlopen
        self.records: list[dict[str, Any]] = []

    def __call__(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        body = json.loads(request.data)
        parts = urlsplit(request.full_url)
        fmt = body.get("format")
        self.records.append(
            {
                "method": request.get_method(),
                "endpoint_class": "loopback"
                if parts.hostname == "127.0.0.1"
                else "NOT_LOOPBACK",
                "path": parts.path,
                "body_keys": sorted(body),
                "model": body.get("model"),
                "stream": body.get("stream"),
                "message_count": len(body.get("messages", ())),
                "format_present": fmt is not None,
                "format_equals_canonical_schema": fmt == self.expected_format,
                "format_sha256": sha256(
                    json.dumps(fmt, sort_keys=True, separators=(",", ":")).encode()
                )
                if fmt is not None
                else None,
                "client_timeout_seconds": kwargs.get("timeout"),
            }
        )
        if len(self.records) > 1:
            raise ValueError("SECOND_PROVIDER_CALL_FORBIDDEN")
        return self.original(request, *args, **kwargs)


def observe(value: Any) -> dict[str, Any]:
    """Deterministic A-I checks against the exact probe schema."""
    is_object = isinstance(value, dict)
    keys = sorted(value) if is_object else []
    extra = sorted(set(keys) - set(FIELDS))
    get = value.get if is_object else (lambda key: None)
    status, label, items, note = (get(k) for k in FIELDS)
    status_ok = isinstance(status, str) and status in STATUS
    label_ok = isinstance(label, str) and len(label) <= LABEL_MAX
    entries: list[Any] | None = items if isinstance(items, list) else None
    items_count_ok = entries is not None and len(entries) <= ITEMS_MAX
    items_elements_ok = entries is not None and all(
        isinstance(x, str) and len(x) <= ITEM_MAX_LENGTH for x in entries
    )
    note_present = is_object and "note" in value
    note_ok = note_present and (
        note is None or (isinstance(note, str) and note in NOTE)
    )
    checks = {
        "A_root_object": is_object,
        "B_exact_declared_properties": is_object and keys == sorted(FIELDS),
        "C_no_additional_property": is_object and not extra,
        "D_status_in_enum": status_ok,
        "E_label_within_max_length": label_ok,
        "F_items_within_max_items": bool(items_count_ok),
        "G_items_elements_valid": bool(items_elements_ok),
        "H_note_nullable_valid": bool(note_ok),
        "I_required_present": is_object and all(k in value for k in FIELDS),
    }
    normalized = {
        "keys": keys[:16],
        "additional_properties": extra[:16],
        "status": status[:32] if isinstance(status, str) else type(status).__name__,
        "label_length": len(label) if isinstance(label, str) else None,
        "items_count": len(entries) if entries is not None else None,
        "item_lengths": [len(x) if isinstance(x, str) else None for x in entries][:16]
        if entries is not None
        else None,
        "note": note[:32] if isinstance(note, str) else type(note).__name__,
    }
    return {"checks": checks, "normalized": normalized}


def parse_one_document(text: str) -> tuple[bool, Any, str | None]:
    def reject(constant: str) -> Any:
        raise ValueError("non-standard constant")

    try:
        return True, json.loads(text, parse_constant=reject), None
    except ValueError as error:
        return False, None, type(error).__name__


async def governed_call(
    fmt: StructuredResponseFormat,
) -> tuple[Any, Any, float]:
    now = datetime.now(UTC)
    ref = ConfigurationRef(
        ApplicationRef(
            ReferenceScope("operator", TenantId("structured-probe")),
            ApplicationId("structured-probe"),
        ),
        "probe",
    )
    host = open_local_host(
        LocalHostConfig(
            ConfigurationRevisionRef(ref, "probe1", Version(1, 0, 0)),
            PrincipalRef("operator", PrincipalId("probe")),
            PolicyRef("operator", "structured-probe", Version(1, 0, 0)),
            (
                OperatorGrant(
                    GrantId("chat"),
                    "invoke-capability",
                    ModelPurpose.CHAT.capability_id.value,
                    now - timedelta(seconds=1),
                    now + timedelta(seconds=TIMEOUT_SECONDS + 10),
                ),
            ),
            (
                ModelBindingConfig(
                    "ollama",
                    ModelRequirement("structured-output-probe"),
                    OllamaSettings(
                        URL, MODEL, MODEL, TIMEOUT_SECONDS, ProviderId("ollama")
                    ),
                ),
            ),
            max_executions=1,  # host-enforced single call
        ),
        {"revision": "probe1", "binding": "ollama"},
        clock=lambda: datetime.now(UTC),
    )
    context = host.model_execution(ModelPurpose.CHAT)
    request = ChatRequest((ChatMessage(ChatRole.USER, PROMPT),), fmt)
    start = time.monotonic()
    outcome = await host.governed_chat(context, request)
    return outcome.execution, outcome.response, time.monotonic() - start


def write(path: Path, data: str) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(data)


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def run(output_root: Path) -> int:
    probe_id = str(uuid.uuid4())
    directory = output_root / f"probe-{probe_id}"
    if directory.exists():
        raise ValueError("OUTPUT_ALREADY_EXISTS")
    record: dict[str, Any] = {
        "probe": PROBE,
        "probe_id": probe_id,
        "approval": APPROVAL,
        "started_at": datetime.now(UTC).isoformat(),
        "semantic_call_ceiling": 1,
        "timeout_seconds": TIMEOUT_SECONDS,
        "retry": False,
        "fallback": False,
    }
    record["repository"] = repository_preconditions()
    observed_version, observed_model, observed_digest = metadata_probe()
    record["runtime"] = {
        "endpoint": URL,
        "endpoint_class": "loopback",
        "url_userinfo": None,
        "credentials": "NONE",
        "ollama_version_expected": VERSION,
        "ollama_version_observed": observed_version,
        "model_tag_expected": MODEL,
        "model_tag_observed": observed_model,
        "model_digest_expected": MODEL_DIGEST,
        "model_digest_observed": observed_digest,
        "platform": platform.platform(),
        "python": platform.python_version(),
    }
    fmt = response_format()
    schema = fmt.json_schema()
    record["request_identity"] = {
        "binding_id": "ollama",
        "binding_provider": "OllamaSettings (built-in local Ollama)",
        "binding_requirement": "structured-output-probe",
        "structured_output_capability": True,  # host-derived for Ollama, ADR-022 §3
        "response_format_present": True,
        "schema_digest": fmt.digest(),
        "schema": schema,
        "prompt_sha256": sha256(PROMPT.encode()),
        "prompt_characters": len(PROMPT),
        "message_count": 1,
    }
    identity_ok = (
        observed_version == VERSION
        and observed_model == MODEL
        and observed_digest == MODEL_DIGEST
    )
    directory.mkdir(parents=True)
    if not identity_ok:
        record["stopped"] = "IDENTITY_MISMATCH_BEFORE_MODEL_CALL"
        record["semantic_calls"] = 0
        write(directory / "run.json", dump(record))
        return report(directory, record, None)
    write(directory / "run.json", dump(record))  # pre-dispatch identity, immutable

    # Process-local transport confinement and narrow wire observation.
    urllib.request.install_opener(build_opener(ProxyHandler({}), NoRedirect()))
    wire = WireObserver(schema)
    urllib.request.urlopen = wire  # type: ignore[assignment]
    result: dict[str, Any] = {}
    try:
        execution, response, elapsed = asyncio.run(governed_call(fmt))
        result["elapsed_seconds"] = round(elapsed, 3)
        result["final_state"] = execution.final_state.name
        result["effect"] = execution.effect.name
        result["error_category"] = (
            execution.error.category.name if execution.error is not None else None
        )
        result["core_returned_text"] = response is not None and isinstance(
            response.content, str
        )
        if response is not None:
            text = response.content
            result["response_model_identity"] = response.model_identity.value
            result["response_provider_identity"] = response.provider_identity.value
            result["response_characters"] = len(text)
            result["response_sha256"] = sha256(text.encode())
            parsed, value, parse_error = parse_one_document(text)
            result["json_parse"] = "SUCCESS" if parsed else "FAILURE"
            result["json_parse_error"] = parse_error
            if parsed:
                result.update(observe(value))
    except Exception as error:  # preserved, never retried
        result["exception"] = type(error).__name__
    finally:
        urllib.request.urlopen = wire.original
    result["semantic_calls"] = len(wire.records)
    result["wire"] = wire.records
    return report(directory, record, result)


def report(
    directory: Path, record: dict[str, Any], result: dict[str, Any] | None
) -> int:
    failures: list[str] = []
    if result is None:
        failures.append("identity mismatch; stopped before model call")
        result = {"semantic_calls": 0}
    else:
        wire = result.get("wire", [])
        checks = result.get("checks", {})
        conditions = {
            "exactly one semantic call": result["semantic_calls"] == 1,
            "governed route reached the Ollama adapter": len(wire) == 1
            and wire[0]["path"] == "/api/chat",
            "loopback endpoint": all(w["endpoint_class"] == "loopback" for w in wire),
            "structured requirement sent as format": bool(wire)
            and wire[0]["format_present"]
            and wire[0]["format_equals_canonical_schema"],
            "no exception": "exception" not in result,
            "execution SUCCEEDED": result.get("final_state") == "SUCCEEDED",
            "effect known and COMPLETED": result.get("effect") == "COMPLETED",
            "Core returned text": result.get("core_returned_text") is True,
            "one parseable JSON document": result.get("json_parse") == "SUCCESS",
            **{f"schema {k}": v for k, v in checks.items()},
        }
        if not checks:
            conditions["schema observations available"] = False
        failures = [name for name, ok in conditions.items() if not ok]
        result["pass_conditions"] = conditions
    verdict = "PASSED" if not failures else "FAILED"
    summary = {
        "probe": PROBE,
        "probe_id": record["probe_id"],
        "finished_at": datetime.now(UTC).isoformat(),
        "verdict": verdict,
        "failures": failures,
        "result": result,
        "interpretation_limit": (
            "One controlled synthetic call with the exact recorded runtime and "
            "model identity. Compatibility evidence only; not statistical "
            "reliability, Agent quality, safety, OpenAI-compatible support or "
            "production readiness."
        ),
    }
    write(directory / "report.json", dump(summary))
    lines = [
        f"# MODEL-STRUCTURED-OUTPUT-1-LIVE-PROBE {verdict}",
        "",
        f"- Probe: `{record['probe_id']}`",
        f"- Git HEAD: `{record['repository']['git_head']}`",
        f"- Ollama: {record['runtime']['ollama_version_observed']}",
        f"- Model: {record['runtime']['model_tag_observed']} "
        f"`{record['runtime']['model_digest_observed']}`",
        f"- Schema digest: `{record['request_identity']['schema_digest']}`",
        f"- Semantic calls: {result['semantic_calls']}",
        f"- Elapsed: {result.get('elapsed_seconds')} s (bound {TIMEOUT_SECONDS:.0f} s)",
        f"- Execution: {result.get('final_state')} / effect {result.get('effect')}",
        f"- JSON parse: {result.get('json_parse')}",
        "",
        "| Condition | Result |",
        "| --- | --- |",
        *(
            f"| {k} | {'yes' if v else 'NO'} |"
            for k, v in result.get("pass_conditions", {}).items()
        ),
        "",
        summary["interpretation_limit"],
        "",
    ]
    write(directory / "report.md", "\n".join(lines))
    print(f"MODEL-STRUCTURED-OUTPUT-1-LIVE-PROBE {verdict}")
    print(directory.relative_to(ROOT).as_posix())
    return 0 if verdict == "PASSED" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.parse_args()
    return run(HERE / "runs")


if __name__ == "__main__":
    raise SystemExit(main())
