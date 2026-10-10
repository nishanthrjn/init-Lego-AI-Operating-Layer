"""CREDENTIAL-HTTPS-T2 boundaries: a private transport, not a policy owner.

The transport imports only the standard library (plus the shared endpoint
normalization), owns no disclosure policy, attempt storage, retry, proxy or
environment input, and is not reachable from the public host or adapters.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRANSPORT = ROOT / "src/legoai/reference/_credential_https.py"
EXCHANGE = ROOT / "src/legoai/runtime/_composition/credential_https.py"


def _imports(path: Path) -> set[str]:
    targets: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.add(node.module)
    return targets


def _names(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name.lower())
        elif isinstance(node, ast.Name):
            names.add(node.id.lower())
        elif isinstance(node, ast.Attribute):
            names.add(node.attr.lower())
    return names


def test_transport_is_stdlib_tls_only() -> None:
    imports = _imports(TRANSPORT)
    legoai = {t for t in imports if t.startswith("legoai")}
    assert legoai == {
        "legoai.governance.disclosure",  # endpoint_parts only
        "legoai.governance.provider_control",  # closed request-shape enum only
    }
    assert not {t.split(".")[0] for t in imports} & {
        "urllib",
        "http",
        "httpx",
        "requests",
        "aiohttp",
        "sqlite3",
        "os",
        "logging",
    }
    assert {"socket", "ssl", "selectors"} <= imports
    names = _names(TRANSPORT)
    assert "evaluate_disclosure" not in names
    for word in (
        "environ",
        "getenv",
        "proxy",
        "retry",
        "redirect",
        "pool",
        "keep_alive",
    ):
        assert not any(word in name for name in names), word
    assert "keylog_filename" in names  # explicitly disabled, never ambient


def test_exchange_owns_no_policy_or_storage() -> None:
    imports = _imports(EXCHANGE)
    assert "legoai.governance.disclosure" not in imports
    assert not {t.split(".")[0] for t in imports} & {
        "sqlite3",
        "socket",
        "os",
        "urllib",
    }
    names = _names(EXCHANGE)
    for word in ("evaluate_disclosure", "admissions", "retry", "fallback", "environ"):
        assert not any(word in name for name in names), word


def test_private_and_unreachable_from_public_paths() -> None:
    importers = set()
    for path in sorted((ROOT / "src").rglob("*.py")):
        if "legoai.reference._credential_https" in _imports(path):
            importers.add(path.relative_to(ROOT).as_posix())
    assert importers == {
        "src/legoai/runtime/_composition/credential_https.py",
        "src/legoai/runtime/_composition/secret.py",
        # OPENAI-COMPATIBLE-REMOTE-1: the REMOTE plane builds the exact target
        # and the verified TLS context; it never touches the flight.
        "src/legoai/runtime/_composition/remote_model.py",
        # PROVIDER-MODEL-DISCOVERY-1: builds the fixed `/models` target.
        "src/legoai/runtime/_composition/provider_discovery.py",
    }
    for public in (
        "src/legoai/runtime/api.py",
        "src/legoai/runtime/local.py",
        "src/legoai/reference/model_openai_compatible.py",
        "src/legoai/reference/model.py",
        "src/legoai/intelligence/model/ports.py",
    ):
        text = (ROOT / public).read_text(encoding="utf-8")
        assert "credential_https" not in text, public
    # No public or adapter module constructs an Authorization header.
    for public in (
        "src/legoai/runtime/api.py",
        "src/legoai/runtime/local.py",
        "src/legoai/reference/model_openai_compatible.py",
        "src/legoai/reference/model.py",
    ):
        text = (ROOT / public).read_text(encoding="utf-8")
        assert "Authorization:" not in text and "Bearer " not in text, public


def test_no_forgeai_engineering_or_provider_specific_code() -> None:
    for path in (TRANSPORT, EXCHANGE):
        assert not any("forgeai" in t or "engineering" in t for t in _imports(path))
        lowered = path.read_text(encoding="utf-8").lower()
        assert "kisski" not in lowered and "openai" not in lowered
