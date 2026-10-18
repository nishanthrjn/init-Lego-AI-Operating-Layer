"""Maintainer-only offline M2 gate. No evaluation, installer or provider client.

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


ROOT = Path(__file__).resolve().parent
AREA = ROOT / "experiments/gemma4_competition"
CANDIDATE = AREA / "baseline"
BASE = "a4cfd4282c3d0ea885554cb9a5159cdb115b44bc"
MODEL = "gemma-4-31b-it-qat-w4a16-ct"
TOOLS = ("run_command", "read_file", "edit_file", "write_file", "get_status", "submit_patch")
MEMBERS = ("agent.yaml", "configs/sampling.yaml", "eval_config.yaml", "prompts/system.md")
SCOPE = {
    *("experiments/gemma4_competition/baseline/" + name for name in MEMBERS),
    "validate_forgeai_gemma4_m2_minimal_baseline_1.py",
    "experiments/gemma4_competition/tests/test_m2_minimal_baseline.py",
    "planning/GEMMA4-IMPLEMENTATION-MILESTONES.md",
}
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


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL)


def scope_checks() -> None:
    changed = set(git("diff", "--name-only", BASE).decode().splitlines())
    changed.update(git("ls-files", "--others", "--exclude-standard").decode().splitlines())
    require(changed <= SCOPE, "outside M2 authoring scope: " + str(sorted(changed - SCOPE)))
    staged = set(git("diff", "--cached", "--name-only", BASE).decode().splitlines())
    for name in staged:
        require(name in SCOPE, "outside staged scope")
        require(normalized(git("show", ":" + name)) == normalized((ROOT / name).read_bytes()),
                "staged content differs: " + name)
    git("diff", "--check", BASE, "--", *sorted(SCOPE))
    git("diff", "--cached", "--check", BASE, "--", *sorted(SCOPE))
    for name in SCOPE:
        data = normalized((ROOT / name).read_bytes())
        require(data.endswith(b"\n"), "missing final newline: " + name)
        require(all(line.rstrip(b" \t") == line for line in data.splitlines()),
                "trailing whitespace: " + name)


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
    data = {name: normalized((directory / name).read_bytes()) for name in MEMBERS}
    require(data == expected_files(), "exact baseline configuration/prompt policy")
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler-worker", action="store_true", help=argparse.SUPPRESS)
    options = parser.parse_args()
    if options.compiler_worker:
        return worker()
    print("[PHASE] exact M2 scope, immutable evidence and static candidate")
    scope_checks()
    wheel_pins()
    data = static_candidate(CANDIDATE)
    print("[PHASE] offline policy and packaging regression controls")
    # Standard-library test suite: no packages, model clients or harness execution.
    subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s",
                    "experiments/gemma4_competition/tests", "-p", "test_m2_minimal_baseline.py"],
                   cwd=ROOT, check=True)
    print("M2_BASELINE_LOCAL_STATIC_CHECKS_PASSED")
    print("[PHASE] metadata preflight and guarded official compiler controls")
    with tempfile.TemporaryDirectory(prefix="gemma-m2-home-") as temporary:
        env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR") if key in os.environ}
        env.update({"HOME": temporary, "USERPROFILE": temporary, "APPDATA": temporary,
                    "LOCALAPPDATA": temporary, "TMP": temporary, "TEMP": temporary,
                    "LITELLM_LOCAL_MODEL_COST_MAP": "True"})
        try:
            result = subprocess.run([sys.executable, "-I", "-B", str(Path(__file__).resolve()),
                                     "--compiler-worker"], cwd=temporary, env=env,
                                    capture_output=True, text=True, timeout=180)
        except subprocess.TimeoutExpired:
            print("OFFICIAL_COMPILER_VALIDATION_BLOCKED_BY_ENVIRONMENT; worker timeout")
            print("M2_BASELINE_INCONCLUSIVE_ENVIRONMENT_BLOCKED")
            return 2
    try:
        report = json.loads(result.stdout)
    except (ValueError, TypeError):
        print("OFFICIAL_COMPILER_VALIDATION_BLOCKED_BY_ENVIRONMENT; worker did not report")
        print("M2_BASELINE_INCONCLUSIVE_ENVIRONMENT_BLOCKED")
        return 2
    if result.returncode == 2:
        print("OFFICIAL_COMPILER_VALIDATION_BLOCKED_BY_ENVIRONMENT; " + report["category"])
        if report.get("missing_distribution"):
            print("missing distribution: " + report["missing_distribution"])
        print("M2_BASELINE_INCONCLUSIVE_ENVIRONMENT_BLOCKED; no package qualification")
        return 2
    require(result.returncode == 0 and report["state"] == "compiler_validated",
            "official compiler controls failed: " + report.get("category", "unknown"))
    print("M2_BASELINE_OFFICIAL_COMPILER_VALIDATED")
    # Recheck after worker; only the exact four normalized source files are packed.
    scope_checks()
    require(static_candidate(CANDIDATE) == data, "candidate changed during validation")
    blob = zip_bytes(data)
    require(blob == zip_bytes(data), "non-deterministic archive")
    inspect_zip(blob, data)
    output = Path(tempfile.mkdtemp(prefix="gemma-m2-package-"))
    with (output / "submission.zip").open("xb") as handle:
        handle.write(blob)
    inspect_zip((output / "submission.zip").read_bytes(), data)
    manifest = {"git_head": git("rev-parse", "HEAD").decode().strip(),
                "baseline": BASE, "zip_sha256": sha(blob), "zip_size": len(blob),
                "members": [{"path": name, "sha256": sha(data[name]), "size": len(data[name])}
                            for name in sorted(data)], "environment": report["versions"],
                "wheel_sha256": {name: sha(path.read_bytes()) for name, path in wheel_pins().items()}}
    with (output / "manifest.json").open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("artifact directory: " + str(output))
    print("ZIP SHA256: " + sha(blob))
    print("M2_BASELINE_PACKAGE_VALIDATED; OFFLINE ONLY; NO KAGGLE ACCEPTANCE, "
          "MODEL QUALITY, LIVE EXECUTION OR SUBMISSION AUTHORIZED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("FAIL: " + type(error).__name__ + "; later phases NOT RUN", file=sys.stderr)
        raise SystemExit(1) from None
