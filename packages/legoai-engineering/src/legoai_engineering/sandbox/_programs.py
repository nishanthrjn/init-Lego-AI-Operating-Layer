"""Fixed container-only programs. Never evaluated by the host interpreter."""

_IDLE = "import time; time.sleep(600)"

_PREPARE = r"""
import base64
import json
import os
import pathlib
import sys

data = json.loads(sys.stdin.buffer.readline(2_000_001))
os.umask(0o077)
for name, content in data["files"]:
    target = pathlib.Path("/work") / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(base64.b64decode(content, validate=True))
pathlib.Path("/work/__legoai__.py").write_bytes(base64.b64decode(data["script"], validate=True))
descriptor = os.open("/dev/null", os.O_RDONLY)
os.dup2(descriptor, 0)
os.close(descriptor)
os.write(1, b"LEGOAI_M6_READY\n")
os.execve(
    "/usr/local/bin/python",
    ["python", "-I", "-B", "/work/__legoai__.py"],
    {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8",
     "HOME": "/nonexistent", "TMPDIR": "/tmp"},
)
"""

_COLLECT = r"""
import base64
import json
import os
import stat
import sys

paths, individual, aggregate = json.loads(sys.argv[1])
result = []
total = 0
try:
    if not os.statvfs("/work").f_flag & os.ST_RDONLY:
        raise ValueError("collector mount is not read-only")
    for path in paths:
        descriptors = []
        try:
            directory = os.open("/work", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            descriptors.append(directory)
            parts = path.split("/")
            for part in parts[:-1]:
                directory = os.open(
                    part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=directory,
                )
                descriptors.append(directory)
            descriptor = os.open(
                parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                dir_fd=directory,
            )
            descriptors.append(descriptor)
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise ValueError("unsupported file")
            if before.st_size > individual or total + before.st_size > aggregate:
                raise ValueError("artifact limit")
            content = bytearray()
            while len(content) <= before.st_size:
                chunk = os.read(descriptor, min(8192, before.st_size + 1 - len(content)))
                if not chunk:
                    break
                content.extend(chunk)
            after = os.fstat(descriptor)
            # Access time can change on read; compare mutation-relevant fields.
            if (len(content) != before.st_size
                or (before.st_ino, before.st_size, before.st_mtime_ns, before.st_nlink)
                != (after.st_ino, after.st_size, after.st_mtime_ns, after.st_nlink)):
                raise ValueError("changed file")
            total += len(content)
            result.append([path, base64.b64encode(content).decode("ascii")])
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)
except (OSError, ValueError):
    sys.exit(74)
sys.stdout.write(json.dumps(result, ensure_ascii=True))
"""
