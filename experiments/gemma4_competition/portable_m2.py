"""Portable maintainer-only compiler gate and explicitly gated Kaggle preparation.

The normal project environment may stop at the explicit environment gate. Run
with an already provisioned compatible interpreter to exercise the official APIs.
"""

from __future__ import annotations

import argparse
import contextlib
from email.parser import BytesParser
import fnmatch
import hashlib
import importlib.metadata as metadata
import io
import json
import os
import re
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
INSTALL_PACKAGES = {**PACKAGES, "google-adk": "1.36.1", "google-genai": "2.11.0"}
INSTALL_AUTHORIZATION = "AUTHORIZE FORGEAI GEMMA4 M2 KAGGLE CPU SCOPED INSTALL AND COMPILER ONLY"
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


def child_environment(source: dict[str, str], home: str) -> tuple[dict[str, str], list[str]]:
    patterns = ("*TOKEN*", "*KEY*", "*SECRET*", "*PASSWORD*", "*CRED*", "KAGGLE_*PROXY*", "HF_*")
    removed = sorted(key for key in source if any(fnmatch.fnmatchcase(key.upper(), p) for p in patterns))
    env = {key: value for key, value in source.items() if key not in removed}
    env.update({"HOME": home, "USERPROFILE": home, "APPDATA": home, "LOCALAPPDATA": home,
                "TMPDIR": home, "TMP": home, "TEMP": home, "CUDA_VISIBLE_DEVICES": "",
                "OTEL_SDK_DISABLED": "true", "LITELLM_LOCAL_MODEL_COST_MAP": "True",
                "LITELLM_TELEMETRY": "False", "PIP_CONFIG_FILE": os.devnull,
                "PIP_DISABLE_PIP_VERSION_CHECK": "1"})
    return env, removed


def install_pins() -> dict[str, dict]:
    register = json.loads((AREA / "source-register.json").read_text(encoding="utf-8"))
    result = {}
    for name, version in INSTALL_PACKAGES.items():
        filename = f"{name.replace('-', '_')}-{version}-py3-none-any.whl"
        entries = [item for item in register["official_files"] if item["path"] == "docs/archive/" + filename]
        require(len(entries) == 1, "missing/ambiguous install pin: " + filename)
        entry = entries[0]
        require(isinstance(entry.get("sha256"), str) and len(entry["sha256"]) == 64,
                "missing install SHA256")
        result[name] = {"filename": filename, "sha256": entry["sha256"], "size": entry["size_bytes"]}
    return result


def select_install_wheels(wheelhouse: Path) -> dict[str, Path]:
    require(wheelhouse.is_dir(), "official wheelhouse input missing")
    duplicates = wheel_pins()
    result = {}
    for name, pin in install_pins().items():
        matches = list(wheelhouse.rglob(pin["filename"]))
        require(len(matches) == 1 and matches[0].is_file(), "missing/ambiguous exact wheel")
        path = matches[0]
        data = path.read_bytes()
        require(len(data) == pin["size"] and sha(data) == pin["sha256"], "install wheel pin mismatch")
        if name in duplicates:
            require(data == duplicates[name].read_bytes(), "bundled wheel mismatch")
        result[name] = path
    require(set(result) == set(INSTALL_PACKAGES), "exact five install wheels required")
    return result


def installed_versions() -> dict[str, str]:
    result = {}
    for name in INSTALL_PACKAGES:
        try:
            result[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            result[name] = "MISSING"
    return result


def direct_requirement_scope(wheels: dict[str, Path]) -> list[str]:
    # Metadata only; no official package imports. Include all declared direct names,
    # even optional ones, when filtering pip's actual environment findings.
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name
    names = set(INSTALL_PACKAGES)
    for path in wheels.values():
        with zipfile.ZipFile(path) as archive:
            members = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")]
            require(len(members) == 1, "wheel METADATA missing/ambiguous")
            message = BytesParser().parsebytes(archive.read(members[0]))
            names.update(canonicalize_name(Requirement(value).name) for value in message.get_all("Requires-Dist", []))
    return sorted(names)


INSTALL_PASS_STATES = {"SCOPED_INSTALL_PASS", "SCOPED_INSTALL_PASS_WITH_OFFICIAL_DEVIATIONS"}


def wheelhouse_contract() -> tuple[list[dict], dict, list[str]]:
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name
    register = json.loads((AREA / "source-register.json").read_text(encoding="utf-8"))
    pins = sorted([{"filename": Path(item["path"]).name, "sha256": item["sha256"],
                    "size": item["size_bytes"]} for item in register["official_files"]
                   if item["path"].startswith("docs/archive/") and item["path"].endswith(".whl")],
                  key=lambda item: item["filename"])
    require(len(pins) == 41 and len({p["filename"] for p in pins}) == 41, "41 unique wheel pins required")
    packages = register["implementation_review"]["packages"]
    by_file = {Path(item["path"]).name: item for item in packages}
    versions = {}
    scope = set(INSTALL_PACKAGES)
    for pin in pins:
        package = by_file[pin["filename"]]
        name = canonicalize_name(package["name"])
        require(name not in versions, "ambiguous wheelhouse distribution")
        versions[name] = package["version"]
        if name in INSTALL_PACKAGES:
            require(package["version"] == INSTALL_PACKAGES[name], "install metadata version mismatch")
            scope.update(canonicalize_name(Requirement(r).name) for r in package["requires_dist"])
    return pins, versions, sorted(scope)


def mounted_inventory(directory: Path) -> list[dict]:
    require(directory.is_dir(), "official wheelhouse input missing")
    result = []
    for path in sorted(directory.rglob("*.whl"), key=lambda p: p.name):
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as stream:
            while block := stream.read(1024 * 1024):
                digest.update(block)
                size += len(block)
        result.append({"filename": path.name, "sha256": digest.hexdigest(), "size": size})
    return result


def parse_pip_line(raw: str) -> dict:
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name
    missing = re.fullmatch(r"(\S+) (\S+) requires (.+), which is not installed\.", raw)
    conflict = re.fullmatch(r"(\S+) (\S+) has requirement (.+), but you have (\S+) (\S+)\.", raw)
    match = missing or conflict
    require(match is not None, "unparseable pip-check line")
    dependent, version, requirement_text = match.group(1, 2, 3)
    requirement = Requirement(requirement_text)
    required = canonicalize_name(requirement.name)
    installed = None
    if conflict:
        require(canonicalize_name(conflict.group(4)) == required, "pip-check requirement identity mismatch")
        installed = conflict.group(5)
    return {"dependent": canonicalize_name(dependent), "dependent_version": version,
            "required_name": required, "kind": "missing" if missing else "version_conflict",
            "installed_version": installed, "requirement": requirement_text, "raw": raw}


def scoped_pip_check(process: subprocess.CompletedProcess, inventory: list[dict], post_versions: dict) -> dict:
    expected, wheel_versions, scope = wheelhouse_contract()
    records, findings, errors = [], [], []
    lines = process.stdout.splitlines()
    # pip's successful sentinel is a status line, not a dependency finding.
    clean = lines == ["No broken requirements found."] and process.returncode == 0
    for raw in ([] if clean else lines):
        try:
            record = parse_pip_line(raw)
        except (ValueError, TypeError):
            errors.append("UNPARSEABLE_LINE")
            continue
        records.append(record)
        if record["dependent"] not in scope:
            continue
        required = record["required_name"]
        pinned = wheel_versions.get(required)
        classification = ("OFFICIAL_ENVIRONMENT_DEVIATION" if pinned is None or
                          record["installed_version"] == pinned else "DIVERGENT_FROM_OFFICIAL")
        if (record["dependent"] in post_versions and
                post_versions[record["dependent"]] != record["dependent_version"]):
            errors.append("DEPENDENT_VERSION_EVIDENCE_MISMATCH")
        if required in post_versions and post_versions[required] != record["installed_version"]:
            errors.append("REQUIRED_VERSION_EVIDENCE_MISMATCH")
        findings.append({**record, "classification": classification})
    acceptable = (inventory == expected and not process.stderr and not errors and
                  ((clean and not records) or (process.returncode == 1 and bool(records))) and
                  all(r["classification"] == "OFFICIAL_ENVIRONMENT_DEVIATION" for r in findings))
    return {"returncode": process.returncode, "stdout": process.stdout, "stderr": process.stderr,
            "scope": scope, "records": records, "findings": findings, "errors": errors,
            "out_of_scope_count": len(records) - len(findings), "acceptable": acceptable}


def install_state(evidence: dict) -> str:
    if (evidence.get("install_returncode") != 0 or evidence.get("post_versions") != INSTALL_PACKAGES
            or not (evidence.get("pip_check") or {}).get("acceptable")):
        return "ENVIRONMENT_BLOCKED"
    return ("SCOPED_INSTALL_PASS_WITH_OFFICIAL_DEVIATIONS" if evidence["pip_check"]["findings"]
            else "SCOPED_INSTALL_PASS")


def scoped_install(authorization: str, receipt: Path, wheelhouse: Path, output: Path) -> dict:
    require(authorization == INSTALL_AUTHORIZATION, "scoped install authorization missing")
    require(sys.platform == "linux" and sys.version_info[:2] == (3, 12), "Python 3.12 Linux required")
    verify_local_receipt(receipt)
    evidence = {"schema": 2, "state": "ENVIRONMENT_BLOCKED",
                "local_receipt_sha256": sha(receipt.read_bytes()), "selected_wheels": install_pins(),
                "pre_versions": installed_versions(), "post_versions": {}, "inventory": [],
                "python": sys.version, "platform": sys.platform, "pip_check": None}
    output.mkdir(parents=True, exist_ok=False)
    try:
        evidence["inventory"] = mounted_inventory(wheelhouse)
        require(evidence["inventory"] == wheelhouse_contract()[0], "wheelhouse inventory mismatch")
        wheels = select_install_wheels(wheelhouse)
        require(direct_requirement_scope(wheels) == wheelhouse_contract()[2], "requirement metadata mismatch")
        with tempfile.TemporaryDirectory(prefix="gemma-install-home-") as home:
            env, removed = child_environment(dict(os.environ), home)
            evidence["removed_environment_names"] = removed
            print(json.dumps({"removed_environment_names": removed}))
            installed = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--no-deps", "--no-index", "--force-reinstall",
                 *(str(wheels[name]) for name in INSTALL_PACKAGES)],
                cwd=home, env=env, capture_output=True, text=True, timeout=300,
            )
            evidence["install_returncode"] = installed.returncode
            evidence["post_versions"] = installed_versions()
            checked = subprocess.run([sys.executable, "-m", "pip", "check"], cwd=home, env=env,
                                     capture_output=True, text=True, timeout=120)
            evidence["pip_check"] = scoped_pip_check(checked, evidence["inventory"], evidence["post_versions"])
            evidence["state"] = install_state(evidence)
    except Exception as error:
        evidence["failure_category"] = type(error).__name__
        evidence["post_versions"] = installed_versions()
    finally:
        with (output / "install-evidence.json").open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return evidence


def verify_install_evidence(path: Path, receipt_hash: str) -> dict:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    require(evidence.get("schema") == 2, "new environment-deviation evidence required")
    require(evidence.get("local_receipt_sha256") == receipt_hash, "install receipt mismatch")
    require(evidence.get("selected_wheels") == install_pins(), "install wheel evidence mismatch")
    require(evidence.get("inventory") == wheelhouse_contract()[0], "wheelhouse inventory mismatch")
    check = evidence.get("pip_check") or {}
    process = subprocess.CompletedProcess([], check.get("returncode"), check.get("stdout", ""), check.get("stderr", ""))
    derived = scoped_pip_check(process, evidence["inventory"], evidence.get("post_versions", {}))
    require(check == derived, "pip-check classification evidence mismatch")
    require(evidence.get("state") == install_state({**evidence, "pip_check": derived})
            and evidence["state"] in INSTALL_PASS_STATES, "scoped install pass missing/mismatched")
    require(set(evidence.get("pre_versions", {})) == set(INSTALL_PACKAGES), "pre-install versions missing")
    require(isinstance(evidence.get("removed_environment_names"), list), "environment evidence missing")
    return evidence


def evidenced_deviation(findings: list[dict], name: str, version: str, requirement,
                       installed: str | None) -> bool:
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name
    for record in findings:
        recorded = Requirement(record["requirement"])
        if (record["classification"] == "OFFICIAL_ENVIRONMENT_DEVIATION"
                and record["dependent"] == canonicalize_name(name)
                and record["dependent_version"] == version
                and record["required_name"] == canonicalize_name(requirement.name)
                and record["installed_version"] == installed
                and record["kind"] == ("missing" if installed is None else "version_conflict")
                # pip omits requirement constraints/extras for missing packages.
                # Missing identity + dependent version + actual absence is exact;
                # version conflicts must also match the reported requirement.
                and (installed is None or (recorded.specifier == requirement.specifier
                                           and recorded.extras == requirement.extras))):
            return True
    return False


def environment_preflight(wheels: dict[str, Path], findings: list[dict] | None = None) -> dict[str, str]:
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
            require(not requirement.url, "direct URL dependency needs separate review")
            try:
                dependency = metadata.distribution(requirement.name)
            except metadata.PackageNotFoundError:
                if evidenced_deviation(findings or [], name, distribution.version, requirement, None):
                    continue
                raise
            if not requirement.specifier.contains(dependency.version):
                require(evidenced_deviation(findings or [], name, distribution.version,
                                           requirement, dependency.version),
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


def worker(receipt: Path | None = None, install_path: Path | None = None) -> int:
    # This child receives a credential-free environment and an empty HOME.
    sys.dont_write_bytecode = True
    sys.addaudithook(deny_effects)
    try:
        require(receipt is not None and install_path is not None, "worker install evidence required")
        verify_local_receipt(receipt)
        install = verify_install_evidence(install_path, sha(receipt.read_bytes()))
        versions = environment_preflight(wheel_pins(), install["pip_check"]["findings"])
    except Exception as error:
        missing = error.name if isinstance(error, metadata.PackageNotFoundError) else None
        print(json.dumps({"state": "environment_blocked", "category": type(error).__name__,
                          "missing_distribution": missing}))
        return 2
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            # Import failures are environment failures, not candidate rejections.
            import google.adk  # noqa: F401
            import google.genai  # noqa: F401
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
        print(json.dumps({"state": "environment_blocked", "stage": "official_compilation",
                          "category": type(error).__name__}))
        return 2
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
    require(output.is_dir() and {p.name for p in output.iterdir()} == {"install-evidence.json"},
            "fresh output containing only install evidence required")
    install_path = output / "install-evidence.json"
    install = verify_install_evidence(install_path, receipt_hash)
    install_hash = sha(install_path.read_bytes())
    with tempfile.TemporaryDirectory(prefix="gemma-m2-home-") as temporary:
        env, removed = child_environment(dict(os.environ), temporary)
        print(json.dumps({"removed_environment_names": removed}), flush=True)
        try:
            process = subprocess.run(
                [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--compiler-worker",
                 "--receipt", str(receipt_path.resolve()), "--install-evidence", str(install_path.resolve())],
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
    require(sha(install_path.read_bytes()) == install_hash, "install evidence changed")
    blob = zip_bytes(data)
    require(blob == zip_bytes(data), "non-deterministic archive")
    inspect_zip(blob, data)
    with (output / "submission.zip").open("xb") as stream:
        stream.write(blob)
    inspect_zip((output / "submission.zip").read_bytes(), data)
    manifest = {
        "schema": 1, "state": "PORTABLE_COMPILE_AND_PACKAGE_PASS",
        "install_evidence": install, "install_evidence_sha256": install_hash,
        "official_environment_deviations": install["pip_check"]["findings"],
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
    parser.add_argument("--install-evidence", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.compiler_worker:
        return worker(args.receipt, args.install_evidence)
    require(args.receipt is not None and args.output is not None, "receipt and fresh output required")
    return run_portable(args.receipt, args.output)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("FAIL: " + type(error).__name__ + "; later phases NOT RUN", file=sys.stderr)
        raise SystemExit(1) from None

