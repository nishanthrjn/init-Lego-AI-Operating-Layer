"""Read-only offline dependency preflight; never imports competition packages.

Uses packaging from the inspection interpreter. Does not resolve from an index,
install, run the M2 validator, or treat metadata compatibility as qualification.
"""

from __future__ import annotations

import argparse
import base64
import csv
from email.parser import Parser
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.tags import compatible_tags, cpython_tags, parse_tag
from packaging.utils import canonicalize_name, parse_wheel_filename


AREA = Path(__file__).resolve().parents[1]
SPEC = Path(__file__).with_name("acquisition-manifest.json")
TARGET = {
    "python_version": "3.12", "python_full_version": "3.12.13",
    "implementation_name": "cpython", "implementation_version": "3.12.13",
    "platform_python_implementation": "CPython", "platform_machine": "AMD64",
    "platform_system": "Windows", "sys_platform": "win32", "os_name": "nt",
}


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def target_tags() -> set:
    return set(cpython_tags((3, 12), abis=["cp312"], platforms=["win_amd64"])) | set(
        compatible_tags((3, 12), interpreter="cp312", platforms=["win_amd64"])
    )


def read_wheel(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        metadata_names = [n for n in names if n.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1:
            raise ValueError("ambiguous wheel METADATA: " + path.name)
        message = Parser().parsestr(archive.read(metadata_names[0]).decode("utf-8"))
    name, version, _, tags = parse_wheel_filename(path.name)
    if canonicalize_name(message["Name"]) != name or str(version) != message["Version"]:
        raise ValueError("wheel filename/metadata identity mismatch: " + path.name)
    return {
        "name": name, "version": str(version), "filename": path.name,
        "requires_python": message.get("Requires-Python", ""),
        "requires_dist": message.get_all("Requires-Dist", []),
        "tags": sorted(map(str, tags)),
    }


def verify_record(path: Path) -> None:
    """Verify selected wheel contents in place; never extract or import them."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        records = [n for n in names if n.endswith(".dist-info/RECORD")]
        if len(records) != 1 or len(names) != len(set(names)):
            raise ValueError("ambiguous wheel RECORD/members: " + path.name)
        rows = list(csv.reader(io.StringIO(archive.read(records[0]).decode("utf-8"))))
        recorded = set()
        for name, hash_value, size in rows:
            member = PurePosixPath(name)
            if member.is_absolute() or ".." in member.parts or "\\" in name or name in recorded:
                raise ValueError("unsafe/duplicate RECORD member: " + path.name)
            recorded.add(name)
            if name == records[0] and not hash_value and not size:
                continue
            algorithm, expected = hash_value.split("=", 1)
            if algorithm not in {"sha256", "sha384", "sha512"}:
                raise ValueError("unsupported RECORD digest: " + path.name)
            with archive.open(name) as stream:
                actual = hashlib.file_digest(stream, algorithm).digest()
            if base64.urlsafe_b64encode(actual).rstrip(b"=").decode() != expected:
                raise ValueError("RECORD digest mismatch: " + path.name)
            if archive.getinfo(name).file_size != int(size):
                raise ValueError("RECORD size mismatch: " + path.name)
        if recorded != {n for n in names if not n.endswith("/")}:
            raise ValueError("RECORD coverage mismatch: " + path.name)


def closure(available: dict[str, dict], roots: list[str], environment: dict) -> dict:
    """Follow known metadata, including extras required by base dependencies.

    A missing node leaves its descendants UNKNOWN. This is not a version solver.
    All incoming constraints are checked against the single supplied version.
    """
    pending = [("ROOT", text) for text in roots]
    edges: dict[str, set[tuple[str, str]]] = {}
    extras: dict[str, set[str]] = {}
    visited = set()
    issues = []
    while pending:
        parent, text = pending.pop()
        requirement = Requirement(text)
        name = canonicalize_name(requirement.name)
        edges.setdefault(name, set()).add((parent, text))
        extras.setdefault(name, set()).update(requirement.extras)
        if requirement.url:
            issues.append({"kind": "DIRECT_URL_REQUIRES_REVIEW", "distribution": name})
        state = (name, tuple(sorted(extras[name])))
        if state in visited:
            continue
        visited.add(state)
        package = available.get(name)
        if package is None:
            continue
        for declaration in package["requires_dist"]:
            dependency = Requirement(declaration)
            if dependency.marker and not any(
                dependency.marker.evaluate(dict(environment, extra=extra))
                for extra in ("", *extras[name])
            ):
                continue
            pending.append((name, declaration))
    for name, incoming in sorted(edges.items()):
        package = available.get(name)
        if package is None:
            issues.append({"kind": "MISSING_DISTRIBUTION_METADATA", "distribution": name,
                           "requirements": [text for _, text in sorted(incoming)]})
            continue
        if not SpecifierSet(package["requires_python"]).contains(environment["python_full_version"]):
            issues.append({"kind": "REQUIRES_PYTHON_MISMATCH", "distribution": name,
                           "requires_python": package["requires_python"]})
        for parent, text in sorted(incoming):
            if not Requirement(text).specifier.contains(package["version"], prereleases=True):
                issues.append({"kind": "SUPPLIED_VERSION_CONSTRAINT_MISMATCH", "distribution": name,
                               "version": package["version"], "parent": parent, "requirement": text})
    return {
        "reachable": sorted(edges),
        "edges": {name: [{"parent": parent, "requirement": text} for parent, text in sorted(values)]
                  for name, values in sorted(edges.items())},
        "required_extras": {name: sorted(values) for name, values in sorted(extras.items()) if values},
        "issues": issues,
        "closure_complete": not any(i["kind"] == "MISSING_DISTRIBUTION_METADATA" for i in issues),
    }


# -I -S suppresses user site, PYTHONPATH and .pth execution. Only stdlib metadata
# reading occurs. Explicit site paths account for Python 3.12's -S venv behavior.
PROBE = r'''
import importlib.metadata as m, json, pathlib, platform, sys, sysconfig
exe = pathlib.Path(sys.executable)
venv = exe.parent.parent if exe.parent.name.lower() in ('scripts', 'bin') else exe.parent
cfg = venv / 'pyvenv.cfg'
if cfg.is_file():
    text = cfg.read_text(encoding='utf-8')
    if any(line.strip().lower() == 'include-system-site-packages = true' for line in text.splitlines()):
        raise RuntimeError('shared site packages refused')
    paths = [venv / 'Lib' / 'site-packages'] if sys.platform == 'win32' else [venv / 'lib' / ('python%d.%d' % sys.version_info[:2]) / 'site-packages']
else:
    paths = [pathlib.Path(sysconfig.get_path('purelib')), pathlib.Path(sysconfig.get_path('platlib'))]
items = []
for d in m.distributions(path=list(dict.fromkeys(map(str, paths)))):
    wheel = d.read_text('WHEEL') or ''
    items.append({'name': d.metadata['Name'], 'version': d.version,
                  'requires_python': d.metadata.get('Requires-Python', ''),
                  'requires_dist': d.requires or [],
                  'tags': [s[5:].strip() for s in wheel.splitlines() if s.startswith('Tag: ')]})
print(json.dumps({'executable': str(exe), 'isolated_venv': cfg.is_file(),
 'environment': {'python_version': '.'.join(map(str, sys.version_info[:2])),
 'python_full_version': platform.python_version(), 'implementation_version': platform.python_version(),
 'implementation_name': sys.implementation.name, 'platform_python_implementation': platform.python_implementation(),
 'platform_machine': platform.machine(), 'platform_system': platform.system(),
 'sys_platform': sys.platform, 'os_name': __import__('os').name,
 'platform_release': platform.release(), 'platform_version': platform.version()}, 'packages': items}))
'''


def inspect_interpreter(path: Path, roots: list[str]) -> dict:
    with tempfile.TemporaryDirectory(prefix="gemma-metadata-home-") as home:
        env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR") if key in os.environ}
        env.update(HOME=home, USERPROFILE=home, APPDATA=home, LOCALAPPDATA=home, TMP=home, TEMP=home)
        process = subprocess.run([str(path), "-I", "-S", "-c", PROBE], cwd=home, env=env,
                                 capture_output=True, text=True, timeout=30)
    if process.returncode:
        return {"executable": str(path), "status": "METADATA_PROBE_FAILED", "exit_code": process.returncode}
    snapshot = json.loads(process.stdout)
    environment = snapshot["environment"]
    if (environment["python_version"], environment["sys_platform"], environment["platform_machine"],
            environment["implementation_name"]) != ("3.12", "win32", "AMD64", "cpython"):
        return {"executable": str(path), "status": "NOT_TARGET_CPYTHON_312_WINDOWS_AMD64",
                "environment": environment}
    packages = {}
    duplicates = []
    for item in snapshot["packages"]:
        name = canonicalize_name(item["name"])
        if name in packages:
            duplicates.append(name)
        packages[name] = item
    analysis = closure(packages, roots, environment)
    for name in analysis["reachable"]:
        if name in packages:
            tags = {tag for text in packages[name]["tags"] for tag in parse_tag(text)}
            if not tags or not tags.intersection(target_tags()):
                analysis["issues"].append({"kind": "INSTALLED_WHEEL_TAG_UNVERIFIED", "distribution": name})
    analysis["issues"].extend({"kind": "AMBIGUOUS_INSTALLED_DISTRIBUTION", "distribution": n} for n in duplicates)
    return {"executable": str(path), "environment": environment,
            "isolated_venv": snapshot["isolated_venv"], "analysis": analysis,
            "status": "INSTALLED_METADATA_COMPATIBLE_NOT_COMPILER_VALIDATED" if not analysis["issues"]
            else "INSTALLED_METADATA_BLOCKED"}


def known_interpreters() -> list[Path]:
    result = [Path(sys.executable)]
    if os.name == "nt":
        home = Path.home()
        result.append(home / "AppData/Local/Programs/Python/Python312/python.exe")
        parent = home / "AppData/Roaming/uv/python"
        if parent.is_dir():
            result.extend(parent.glob("cpython-3.12*-windows-x86_64-none/python.exe"))
    return list(dict.fromkeys(p.absolute() for p in result if p.is_file()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", action="append", type=Path, help="Existing trusted Python executable; repeatable")
    parser.add_argument("--report", type=Path, help="New JSON report path; refuses overwrite")
    args = parser.parse_args()
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    constraints = [line.strip() for line in Path(__file__).with_name("constraints.txt").read_text().splitlines()
                   if line.strip() and not line.lstrip().startswith("#")]
    roots = list(dict.fromkeys([*spec["roots"], *constraints]))
    register = json.loads((AREA / "source-register.json").read_text(encoding="utf-8"))
    pins = {item["path"]: item for item in register["official_files"] if item["path"].endswith(".whl")}
    available, paths = {}, {}
    for relative in sorted(pins):
        path = AREA / relative
        item = read_wheel(path)
        if item["name"] in available:
            raise ValueError("multiple archive versions require explicit resolution: " + item["name"])
        available[item["name"]] = item
        paths[item["name"]] = (relative, path)
    environment = dict(default_environment(), **TARGET)
    analysis = closure(available, roots, environment)
    verified = []
    for name in analysis["reachable"]:
        if name not in available:
            continue
        relative, path = paths[name]
        pin = pins[relative]
        if path.is_symlink() or path.stat().st_size != pin["size_bytes"] or digest(path) != pin["sha256"]:
            raise ValueError("preserved source-register wheel pin mismatch: " + path.name)
        verify_record(path)
        verified.append({"file": path.name, "sha256": pin["sha256"], "record_verified": True})
        tags = {tag for text in available[name]["tags"] for tag in parse_tag(text)}
        if not tags.intersection(target_tags()):
            analysis["issues"].append({"kind": "UNSUPPORTED_TARGET_WHEEL_TAG", "distribution": name,
                                       "file": path.name, "tags": available[name]["tags"]})
    interpreters = []
    for executable in args.python or known_interpreters():
        try:
            interpreters.append(inspect_interpreter(executable.absolute(), roots))
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            interpreters.append({"executable": str(executable), "status": "METADATA_PROBE_FAILED",
                                 "category": type(error).__name__})
    report = {"task": spec["task"], "target": TARGET, "archive": analysis,
              "verified_selected_wheels": verified, "interpreters": interpreters,
              "qualification": "NO_M2_QUALIFICATION; METADATA_ONLY; NO_INSTALL_OR_NETWORK"}
    if args.report:
        with args.report.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, sort_keys=True)
            stream.write("\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    if analysis["issues"]:
        print("COMPILER_ENVIRONMENT_ARCHIVE_BLOCKED; acquisition/resolution review required")
    if any(item["status"] == "INSTALLED_METADATA_COMPATIBLE_NOT_COMPILER_VALIDATED" for item in interpreters):
        print("EXISTING_ENVIRONMENT_METADATA_COMPATIBLE; actual M2 gate still required")
        return 0
    print("COMPILER_ENVIRONMENT_BLOCKED; NO_M2_QUALIFICATION")
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("PREFLIGHT_FAILED: " + type(error).__name__ + ": " + str(error), file=sys.stderr)
        raise SystemExit(1) from None
