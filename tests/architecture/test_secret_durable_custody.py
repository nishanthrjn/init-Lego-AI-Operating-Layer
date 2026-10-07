"""Scope/dependency guards for the durable prerequisite, not Stage-A authority."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (
    "src/legoai/governance/secret.py",
    "src/legoai/evidence/custody.py",
    "src/legoai/reference/_custody_codec.py",
    "src/legoai/reference/_custody_sqlite.py",
    "src/legoai/reference/_secret_domain.py",
    "src/legoai/reference/_durable_evidence.py",
    "src/legoai/reference/_secret_ledger.py",
)


def test_accepted_decision():
    text = (ROOT / "planning/LEGOAI-SECRET-USE-DURABLE-CUSTODY-DECISION.md").read_text(
        encoding="utf-8"
    )
    assert "**Status: ACCEPTED" in text
    assert "SECRET-SPECIFIC DURABLE USE LEDGER JUSTIFIED" in text
    assert "Stage A remains stopped" in text


def test_no_provider_environment_or_network():
    forbidden = {
        "socket",
        "http",
        "httpx",
        "requests",
        "urllib",
        "subprocess",
        "asyncio",
        "multiprocessing",
        "os",
    }
    for name in SOURCE:
        tree = ast.parse((ROOT / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not {n.name.split(".")[0] for n in node.names} & forbidden
            elif isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in forbidden


def test_public_surface():
    for name in SOURCE[:2]:
        tree = ast.parse((ROOT / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith(
                    ("sqlite3", "legoai.reference", "legoai.runtime")
                )
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                assert node.target.id not in {
                    "material",
                    "header",
                    "callback",
                    "token",
                    "connection",
                    "transaction",
                }


def test_no_independent_consumer_callback():
    tree = ast.parse((ROOT / SOURCE[-1]).read_text(encoding="utf-8"))
    method = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "accept"
    )
    assert not any(
        isinstance(n, (ast.Await, ast.AsyncFunctionDef)) for n in ast.walk(method)
    )
    calls = [n.func for n in ast.walk(method) if isinstance(n, ast.Call)]
    assert not any(
        isinstance(n, ast.Name) and n.id in {"callback", "consumer", "submit", "invoke"}
        for n in calls
    )
    assert sum(isinstance(n, ast.Name) and n.id == "_commit" for n in calls) == 1
    assert not any(
        isinstance(n, ast.Attribute)
        and n.attr in {"acknowledge", "submission_status", "witness"}
        for n in calls
    )


def test_owner_separation():
    source = (ROOT / SOURCE[-1]).read_text(encoding="utf-8")
    custody = (ROOT / SOURCE[-2]).read_text(encoding="utf-8")
    for text in (source, custody):
        assert "SQLiteConfigurationStore" not in text
        assert "CREATE TABLE config_" not in text
    assert "CREATE TABLE custody" not in source
    assert "CREATE TABLE accepted" not in custody
    # The common helper contains SQLite mechanics only, not an owner mutation API.
    helper = (ROOT / SOURCE[3]).read_text(encoding="utf-8")
    assert "class Transaction" not in helper
    assert "CREATE TABLE accepted" not in helper
