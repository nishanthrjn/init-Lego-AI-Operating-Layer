"""Stage-A scope, owner separation and prerequisite guards."""

import ast
from pathlib import Path

from legoai.governance.ports import SecretAccessPort
from tests.architecture.test_import_boundaries import violations

ROOT = Path(__file__).resolve().parents[2]


def test_accepted_secret_scope():
    text = (ROOT / "planning/LEGOAI-SECRET-REF-1-DECISION.md").read_text(
        encoding="utf8"
    )
    assert "**Status: ACCEPTED" in text
    assert "SECRET-REF-1B" in text


def test_accepted_arbitration():
    text = (ROOT / "planning/LEGOAI-SECRET-REF-1A-ARBITRATION-DECISION.md").read_text(
        encoding="utf8"
    )
    assert "**Status: ACCEPTED" in text
    assert "shared process-local ordering domain" in text


def test_qualified_durable_prerequisite():
    text = (ROOT / "planning/LEGOAI-SECRET-USE-DURABLE-CUSTODY-DECISION.md").read_text(
        encoding="utf8"
    )
    assert "LOCALLY QUALIFIED" in text and "72" in text
    for name in ("_secret_ledger.py", "_durable_evidence.py", "_secret_domain.py"):
        assert (ROOT / "src/legoai/reference" / name).is_file()


def test_public_operations_no_material():
    names = {name for name in vars(SecretAccessPort) if not name.startswith("_")}
    assert names == {
        "resolve_secret_reference",
        "authorize_secret_use",
        "validate_secret_revision",
        "record_secret_use",
    }
    for path in ("src/legoai/governance/secret.py", "src/legoai/governance/ports.py"):
        source = (ROOT / path).read_text(encoding="utf8")
        assert not violations({path[4:-3].replace("/", "."): source})


def test_secret_owner_separation():
    source = (ROOT / "src/legoai/reference/secret.py").read_text(encoding="utf8")
    imports = [
        n.module for n in ast.walk(ast.parse(source)) if isinstance(n, ast.ImportFrom)
    ]
    assert set(imports) <= {
        "datetime",
        "secrets",
        "legoai.governance.ports",
        "legoai.governance.secret",
        # SECRET-SOURCE-S1: identity validation and the owner's scope (kernel).
        "legoai.kernel.identity",
        "legoai.kernel.references",
        "legoai.reference._secret_domain",
    }
    for name in ("reference/secret.py", "runtime/_composition/secret.py"):
        tree = ast.parse((ROOT / "src/legoai" / name).read_text(encoding="utf8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not {a.name.split(".")[0] for a in node.names} & {
                    "os",
                    "socket",
                    "http",
                    "urllib",
                    "asyncio",
                    "subprocess",
                    "concurrent",
                }
            if isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in {
                    "os",
                    "socket",
                    "http",
                    "urllib",
                    "asyncio",
                    "subprocess",
                    "concurrent",
                }
            assert not isinstance(node, (ast.AsyncFunctionDef, ast.Await))
    # Shared domain owns no authority records, persistence or callbacks.
    source = (ROOT / "src/legoai/reference/_secret_domain.py").read_text(
        encoding="utf8"
    )
    assert "sqlite" not in source and "Grant" not in source


def test_gate_has_no_custody_io_or_callback():
    tree = ast.parse(
        (ROOT / "src/legoai/runtime/_composition/secret.py").read_text(encoding="utf8")
    )
    method = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "_accept"
    )
    gate = next(
        n
        for n in ast.walk(method)
        if isinstance(n, ast.With)
        and any(
            isinstance(c, ast.Call)
            and isinstance(c.func, ast.Attribute)
            and c.func.attr == "_current"
            for c in ast.walk(n)
        )
    )
    calls = {
        n.func.attr
        for n in ast.walk(gate)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    }
    assert "accept" in calls
    assert not calls & {
        "acknowledge",
        "witness",
        "submission_status",
        "submit",
        "to_thread",
        "create_task",
        "arbitrate",
        "claim_invocation",
    }
    assert not any(
        isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id in {"callback", "consumer"}
        for n in ast.walk(gate)
    )
