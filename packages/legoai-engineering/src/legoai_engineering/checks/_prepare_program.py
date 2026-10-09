"""Fixed preparation program; runs only in a dedicated network-enabled container.

No target source is supplied. Never imports newly acquired dependency code.
"""

_INSTALL = r"""
import importlib.metadata, json, os, pathlib, re, site, subprocess, sys, zipfile
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

def finish(reason):
    print(json.dumps({"status": reason}), flush=True)
    sys.exit(0 if reason == "prepared" else 1)

data = json.loads(sys.stdin.buffer.readline(524289))
if sys.version.split()[0] != "3.14.7":
    finish("prepared_image_identity_invalid")
if not SpecifierSet(data["python"]).contains(sys.version.split()[0]):
    finish("python_incompatible")
root = pathlib.Path("/opt/legoai-project-deps")
base = pathlib.Path(site.getsitepackages()[0])
protected = set(sys.stdlib_module_names)
protected.update(p.name.split(".")[0] for p in base.iterdir())
protected.update({"sitecustomize", "usercustomize"})
installed = {re.sub(r"[-_.]+", "-", d.metadata["Name"]).lower(): d.version
             for d in importlib.metadata.distributions()}
selected = []
for line in data["requirements"].replace("\\\n", " ").splitlines():
    if not line.strip():
        continue
    requirement, *hashes = line.split(" --hash=")
    req = Requirement(requirement.strip())
    if req.url or not hashes or any(not re.fullmatch(r"sha256:[0-9a-f]{64}", h.strip()) for h in hashes):
        finish("lock_invalid")
    pins = list(req.specifier)
    if len(pins) != 1 or pins[0].operator != "==" or "*" in pins[0].version:
        finish("lock_invalid")
    if req.marker and not req.marker.evaluate():
        continue
    name = re.sub(r"[-_.]+", "-", req.name).lower()
    if name in installed:
        if installed[name] != pins[0].version:
            finish("unsupported_project")
        continue
    selected.append(line)
pathlib.Path("/tmp/requirements.txt").write_text("\n".join(selected), encoding="utf-8")
root.mkdir()
if selected:
    pathlib.Path("/tmp/wheels").mkdir()
    # Files live on a bounded tmpfs; stdout is a small closed status envelope.
    with open("/tmp/pip.log", "w+b") as log:
        try:
            result = subprocess.run([
                "/usr/local/bin/python", "-I", "-m", "pip", "--isolated",
                "download", "--disable-pip-version-check", "--no-input", "--no-cache-dir",
                "--no-deps", "--only-binary=:all:", "--require-hashes",
                "--retries", "0", "--timeout", "20", "--index-url", "https://pypi.org/simple",
                "--dest", "/tmp/wheels", "--requirement", "/tmp/requirements.txt",
            ], stdin=subprocess.DEVNULL, stdout=log, stderr=log, timeout=240, shell=False,
               env={"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/nonexistent",
                    "TMPDIR": "/tmp", "PIP_CONFIG_FILE": "/dev/null"})
        except subprocess.TimeoutExpired:
            finish("preparation_timeout")
        if result.returncode:
            log.seek(0)
            output = log.read(65536).lower()
            if any(s in output for s in (b"connection", b"timed out", b"sslerror", b"network is unreachable")):
                finish("preparation_network_failed")
            if b"no matching distribution" in output or b"could not find a version" in output:
                finish("dependency_unavailable")
            finish("preparation_tool_failed")
    count = total = 0
    for wheel in pathlib.Path("/tmp/wheels").iterdir():
        if wheel.suffix != ".whl":
            finish("dependency_unavailable")
        with zipfile.ZipFile(wheel) as archive:
            for item in archive.infolist():
                count += 1
                total += item.file_size
                parts = pathlib.PurePosixPath(item.filename).parts
                if (not parts or item.filename.startswith("/") or ".." in parts
                    or "\\" in item.filename or item.filename.endswith(".pth")
                    or (item.external_attr >> 16) & 0o170000 == 0o120000
                    or parts[0].split(".")[0] in protected
                    or count > 8192 or total > 134217728):
                    finish("unsupported_project")
    # Installation has no registry access and no source builds; hashes are verified again.
    with open("/tmp/install.log", "w+b") as log:
        try:
            result = subprocess.run([
                "/usr/local/bin/python", "-I", "-m", "pip", "--isolated", "install",
                "--disable-pip-version-check", "--no-input", "--no-cache-dir", "--no-compile",
                "--no-deps", "--only-binary=:all:", "--require-hashes", "--no-index",
                "--find-links", "/tmp/wheels", "--target", str(root),
                "--requirement", "/tmp/requirements.txt",
            ], stdin=subprocess.DEVNULL, stdout=log, stderr=log, timeout=30, shell=False,
               env={"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/nonexistent",
                    "TMPDIR": "/tmp", "PIP_CONFIG_FILE": "/dev/null"})
        except subprocess.TimeoutExpired:
            finish("preparation_timeout")
        if result.returncode:
            finish("preparation_tool_failed")
# Refuse import shadowing and startup hooks; do not run third-party code to probe it.
for path in root.iterdir():
    if path.name.split(".")[0] in protected:
        finish("unsupported_project")
count = total = 0
for path in root.rglob("*"):
    count += 1
    if path.is_symlink() or path.suffix == ".pth":
        finish("unsupported_project")
    if path.is_file():
        total += path.stat().st_size
    if count > 8192 or total > 134217728:
        finish("unsupported_project")
# This fixed path is appended AFTER base tooling. Dependency .pth files are not processed.
(base / "legoai_project_dependencies.pth").write_text(str(root) + "\n")
pathlib.Path("/opt/legoai-prepared.json").write_text(json.dumps(data["identity"], sort_keys=True))
finish("prepared")
"""
