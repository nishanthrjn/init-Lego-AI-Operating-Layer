"""Portable maintainer-only compiler gate. No Git, evaluation or installer.

The normal project environment may stop at the explicit environment gate. Run
with an already provisioned compatible interpreter to exercise the official APIs.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.metadata as metadata
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile


AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[1]
CANDIDATE = AREA / "baseline"
BASE = "a4cfd4282c3d0ea885554cb9a5159cdb115b44bc"
MODEL = "gemma-4-31b-it-qat-w4a16-ct"
TOOLS = ("run_command", "read_file", "edit_file", "write_file", "get_status", "submit_patch")
MEMBERS = ("agent.yaml", "configs/sampling.yaml", "eval_config.yaml", "prompts/system.md")
PACKAGES = {"adk-submission": "0.2.13", "adk-eval-core": "0.1.0", "swegemma": "0.2.11"}
SAMPLING = """temperature: 0.2
top_p: 0.95
max_output_tokens: 16384
thinking_config:
  thinking_budget: 4096
  include_thoughts: true
"""
EVALUATION = """evaluation:
  timeout_seconds: 60
  max_tool_calls: 10
  max_time_minutes: 1
  max_turns: 50
"""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def normalized(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def expected_files() -> dict[str, bytes]:
    # The approved prompt remains sourced from the preserved contract register.
    register = (AREA / "OFFICIAL-CONTRACT-REGISTER.md").read_text(encoding="utf-8")
    prompt = register.split("Exact proposed system instruction for the future file:\n\"", 1)[1]
    prompt = prompt.split('\"\nThis is prompt policy', 1)[0] + "\n"
    agent = f"name: forgeai_gemma4_baseline\nagent_class: LlmAgent\nmodel: {MODEL}\n"
    agent += "instruction: !include prompts/system.md\ntools:\n"
    agent += "".join(f"  - {tool}\n" for tool in TOOLS)
    agent += "generate_content_config: !include configs/sampling.yaml\n"
    return {name: value.encode() for name, value in zip(
        MEMBERS, (agent, SAMPLING, EVALUATION, prompt), strict=True
    )}


def static_candidate(directory: Path) -> dict[str, bytes]:
    require(not directory.is_symlink() and not directory.is_junction(), "candidate link")
    paths = list(directory.rglob("*"))
    for path in paths:
        require(not path.is_symlink() and not path.is_junction(), "link or junction")
        require(path.is_file() or path.is_dir(), "special file")
        if path.is_file():
            require(path.stat().st_size < 64 * 1024, "baseline source size bound")
    files = {path.relative_to(directory).as_posix() for path in paths if path.is_file()}
    dirs = {path.relative_to(directory).as_posix() for path in paths if path.is_dir()}
    require(files == set(MEMBERS) and dirs == {"configs", "prompts"}, "exact four-file layout")
    data = {name: (directory / name).read_bytes() for name in MEMBERS}
    require(data == expected_files(), "exact LF baseline configuration/prompt policy")
    return data


def wheel_pins() -> dict[str, Path]:
    register = json.loads((AREA / "source-register.json").read_text(encoding="utf-8"))
    entries = {item["path"]: item for item in register["official_files"]}
    result = {}
    for name, version in PACKAGES.items():
        relative = f"docs/archive/{name.replace('-', '_')}-{version}-py3-none-any.whl"
        path = AREA / relative
        entry = entries[relative]
        require(path.stat().st_size == entry["size_bytes"], "wheel size changed")
        require(sha(path.read_bytes()) == entry["sha256"], "wheel pin changed")
        result[name] = path
    return result


def environment_preflight(wheels: dict[str, Path]) -> dict[str, str]:
    """Inspect metadata before importing any official package; never install."""
    versions = {}
    for name, version in {**PACKAGES, "google-adk": "1.36.1", "google-genai": "2.11.0"}.items():
        distribution = metadata.distribution(name)
        require(distribution.version == version, "incompatible distribution: " + name)
        versions[name] = distribution.version
        if name in wheels:
            with zipfile.ZipFile(wheels[name]) as archive:
                for member in archive.namelist():
                    if member.endswith(".py") or member.endswith("/METADATA"):
                        installed = Path(distribution.locate_file(member))
                        require(installed.read_bytes() == archive.read(member),
                                "installed bytes differ from supplied wheel: " + name)
    # packaging is metadata tooling, not a provider or official compiler import.
    from packaging.requirements import Requirement
    from packaging.specifiers import SpecifierSet

    pending = list(versions)
    seen = set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        distribution = metadata.distribution(name)
        python_spec = distribution.metadata.get("Requires-Python", "")
        require(SpecifierSet(python_spec).contains(".".join(map(str, sys.version_info[:3]))),
                "incompatible Python requirement: " + name)
        versions[name] = distribution.version
        for text in distribution.requires or []:
            requirement = Requirement(text)
            if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
                continue
            dependency = metadata.distribution(requirement.name)
            require(not requirement.url, "direct URL dependency needs separate review")
            require(requirement.specifier.contains(dependency.version),
                    "dependency version mismatch: " + requirement.name)
            pending.append(requirement.name)
    return versions


class OfflineViolation(RuntimeError):
    pass


def deny_effects(event: str, args: tuple) -> None:
    if event.startswith(("socket.", "subprocess.", "os.exec", "os.spawn")) or event == "os.system":
        raise OfflineViolation("network/process effect refused")
    if event == "open" and args and isinstance(args[0], (str, bytes)):
        path = os.fsdecode(args[0]).replace("\\", "/").lower()
        parts = path.split("/")
        if any(part in {".aws", ".azure", ".ssh", ".netrc", "credentials.json",
                        "application_default_credentials.json"} for part in parts):
            raise OfflineViolation("credential file access refused")
        if parts[-1] == ".env" or parts[-1].startswith(".env."):
            raise OfflineViolation("dotenv access refused")


def official_controls() -> None:
    """Executed only by the maintainer in the isolated child interpreter."""
    import adk_submission as official
    from adk_submission.context import AgentClassFactory
    from adk_submission.errors import SubmissionError
    from swegemma.config import build_submission_limits

    limits, constraints = build_submission_limits()
    tools = official.ToolRegistry()

    def forbidden_tool(*args, **kwargs):
        raise OfflineViolation("tool invocation refused")

    for name in TOOLS:
        tools.register(name, forbidden_tool)

    class InertModel:
        def generate_content_async(self, *args, **kwargs):
            raise OfflineViolation("inference refused")

    class InertAgent:
        def __init__(self, **kwargs):
            self.values = kwargs

    models = official.ModelRegistry()
    models.register(MODEL, InertModel())

    def compile_candidate(path):
        official.validate_directory(path, limits=limits)
        return official.compile_submission(
            path, tool_registry=tools, model_registry=models, limits=limits,
            generation_constraints=constraints,
            agent_factory=AgentClassFactory(agent_cls=InertAgent),
        )

    with tempfile.TemporaryDirectory(prefix="gemma-m2-compiler-") as temporary:
        root = Path(temporary)
        positive = root / "positive"
        shutil.copytree(CANDIDATE, positive)
        compiled = compile_candidate(positive).values
        require(compiled["name"] == "forgeai_gemma4_baseline", "compiled identity")
        require(isinstance(compiled["model"], InertModel), "compiled inert model")
        require(compiled["instruction"].encode() == expected_files()["prompts/system.md"],
                "compiled prompt")
        require(compiled["tools"] == [forbidden_tool] * 6 and not compiled["sub_agents"],
                "compiled tools/subagents")
        generation = compiled["generate_content_config"]
        require(generation.temperature == 0.2 and generation.top_p == 0.95
                and generation.max_output_tokens == 16384
                and generation.thinking_config.thinking_budget == 4096
                and generation.thinking_config.include_thoughts is True, "compiled sampling")
        mutations = {
            "unknown-field": ("agent.yaml", "agent_class: LlmAgent", "agent_class: LlmAgent\nunknown: true"),
            "unknown-tool": ("agent.yaml", "  - read_file", "  - missing_tool"),
            "unknown-model": ("agent.yaml", MODEL, "unregistered-model"),
            "output-bound": ("configs/sampling.yaml", "16384", "32769"),
            "include-escape": ("agent.yaml", "prompts/system.md", "../outside.md"),
        }
        (root / "outside.md").write_text("outside", encoding="utf-8")
        for label, (name, old, new) in mutations.items():
            copy = root / label
            shutil.copytree(positive, copy)
            path = copy / name
            path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
            try:
                compile_candidate(copy)
            except SubmissionError:
                pass
            else:
                raise ValueError("official negative control accepted: " + label)


def worker() -> int:
    # This child receives a credential-free environment and an empty HOME.
    sys.dont_write_bytecode = True
    sys.addaudithook(deny_effects)
    try:
        versions = environment_preflight(wheel_pins())
    except Exception as error:
        missing = error.name if isinstance(error, metadata.PackageNotFoundError) else None
        print(json.dumps({"state": "environment_blocked", "category": type(error).__name__,
                          "missing_distribution": missing}))
        return 2
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            # Import failures are environment failures, not candidate rejections.
            import adk_submission  # noqa: F401
            from swegemma.config import build_submission_limits  # noqa: F401
    except Exception as error:
        print(json.dumps({"state": "environment_blocked", "category": type(error).__name__}))
        return 2
    try:
        # Suppress third-party logs; return bounded diagnostics, never raw errors.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            official_controls()
    except (ImportError, OfflineViolation) as error:
        print(json.dumps({"state": "environment_blocked", "category": type(error).__name__}))
        return 2
    except Exception as error:
        print(json.dumps({"state": "compiler_failed", "category": type(error).__name__}))
        return 1
    print(json.dumps({"state": "compiler_validated", "versions": versions}))
    return 0


def zip_bytes(data: dict[str, bytes]) -> bytes:
    require(set(data) == set(MEMBERS), "archive member policy")
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(data):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, data[name])
    return stream.getvalue()


def inspect_zip(blob: bytes, expected: dict[str, bytes]) -> None:
    require(len(blob) < 1024 * 1024, "baseline archive must stay below 1 MiB")
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        require(archive.namelist() == sorted(MEMBERS), "archive root/order/member mismatch")
        for info in archive.infolist():
            require(info.file_size == len(expected[info.filename]), "member size mismatch")
            require(info.compress_type == zipfile.ZIP_STORED and info.flag_bits & 1 == 0,
                    "unexpected compression/encryption")
            require(info.create_system == 3 and info.external_attr >> 16 == stat.S_IFREG | 0o644,
                    "archive mode/link mismatch")
            require(info.date_time == (1980, 1, 1, 0, 0, 0), "archive timestamp")
            require(archive.read(info) == expected[info.filename], "archive bytes mismatch")


def transfer_paths() -> list[str]:
    prefix = "experiments/gemma4_competition/"
    return sorted([
        "validate_forgeai_gemma4_m2_minimal_baseline_1.py",
        prefix + "portable_m2.py",
        prefix + "tests/test_m2_minimal_baseline.py",
        prefix + "kaggle_compiler/compiler_only.ipynb",
        prefix + "OFFICIAL-CONTRACT-REGISTER.md",
        prefix + "source-register.json",
        *(prefix + "baseline/" + name for name in MEMBERS),
        *(prefix + f"docs/archive/{name.replace('-', '_')}-{version}-py3-none-any.whl"
          for name, version in PACKAGES.items()),
    ])


def input_manifest() -> dict:
    result = {}
    for name in transfer_paths():
        path = ROOT / name
        require(not path.is_symlink() and path.is_file(), "unsafe/missing input: " + name)
        data = path.read_bytes()
        result[name] = {"sha256": sha(data), "size": len(data)}
    return result


def verify_local_receipt(path: Path) -> dict:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    require(receipt.get("schema") == 1 and receipt.get("state") == "LOCAL_SCOPE_AND_STATIC_PASS",
            "missing local scope/static pass")
    require(receipt.get("inputs") == input_manifest(), "local/portable byte identity mismatch")
    static_candidate(CANDIDATE)
    return receipt


def run_portable(receipt_path: Path, output: Path) -> int:
    verify_local_receipt(receipt_path)
    receipt_hash = sha(receipt_path.read_bytes())
    data = static_candidate(CANDIDATE)
    for name in sorted(data):
        print("CANDIDATE_SHA256 " + sha(data[name]) + " " + name, flush=True)
    wheel_pins()
    output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix="gemma-m2-home-") as temporary:
        env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR") if key in os.environ}
        env.update({"HOME": temporary, "USERPROFILE": temporary, "APPDATA": temporary,
                    "LOCALAPPDATA": temporary, "TMP": temporary, "TEMP": temporary,
                    "LITELLM_LOCAL_MODEL_COST_MAP": "True", "CUDA_VISIBLE_DEVICES": "",
                    "OTEL_SDK_DISABLED": "true", "LITELLM_TELEMETRY": "False"})
        try:
            process = subprocess.run(
                [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--compiler-worker"],
                cwd=temporary, env=env, capture_output=True, text=True, timeout=180,
            )
            report = json.loads(process.stdout)
            code = process.returncode
        except (subprocess.TimeoutExpired, ValueError):
            report = {"state": "environment_blocked", "category": "WorkerUnavailable"}
            code = 2
    # Only bounded, structured worker output is retained, never third-party raw logs.
    (output / "compiler-output.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    if code != 0:
        print("M2_BASELINE_INCONCLUSIVE_ENVIRONMENT_BLOCKED" if code == 2 else "PORTABLE_COMPILER_FAILED")
        return code
    require(report.get("state") == "compiler_validated", "compiler did not validate")
    verify_local_receipt(receipt_path)
    require(sha(receipt_path.read_bytes()) == receipt_hash, "receipt changed")
    require(static_candidate(CANDIDATE) == data, "candidate changed")
    blob = zip_bytes(data)
    require(blob == zip_bytes(data), "non-deterministic archive")
    inspect_zip(blob, data)
    with (output / "submission.zip").open("xb") as stream:
        stream.write(blob)
    inspect_zip((output / "submission.zip").read_bytes(), data)
    manifest = {
        "schema": 1, "state": "PORTABLE_COMPILE_AND_PACKAGE_PASS",
        "local_receipt_sha256": receipt_hash, "inputs": input_manifest(),
        "python": sys.version, "platform": sys.platform, "environment": report["versions"],
        "zip_sha256": sha(blob), "zip_size": len(blob),
        "members": [{"path": name, "sha256": sha(data[name]), "size": len(data[name])}
                    for name in sorted(data)],
        "wheel_sha256": {name: sha(path.read_bytes()) for name, path in wheel_pins().items()},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print("PORTABLE_COMPILE_AND_PACKAGE_PASS; LOCAL RECONCILIATION REQUIRED; NO LIVE OR SUBMISSION AUTHORIZATION")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.compiler_worker:
        return worker()
    require(args.receipt is not None and args.output is not None, "receipt and fresh output required")
    return run_portable(args.receipt, args.output)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("FAIL: " + type(error).__name__ + "; later phases NOT RUN", file=sys.stderr)
        raise SystemExit(1) from None

