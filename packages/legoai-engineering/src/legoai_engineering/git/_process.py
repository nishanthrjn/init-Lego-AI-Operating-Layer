"""Private fixed status invocation and bounded dual-pipe capture."""

import os
import subprocess
import time
from enum import Enum
from pathlib import Path

from legoai_engineering.git.errors import GitError, GitFailure


class GitCommand(Enum):
    INDEX = "index"
    STATUS = "status"


def capture(
    executable: Path,
    root: Path,
    timeout: int,
    output_limit: int,
    command: GitCommand,
) -> bytes:
    if type(command) is not GitCommand:
        raise TypeError("private command requires GitCommand")
    # No inherited Git, HOME, PATH, loader, tracing or credential settings.
    environment = {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_ATTR_NOSYSTEM": "1",
        "LC_ALL": "C",
    }
    # Windows needs its system directory to load the trusted installed program.
    if os.name == "nt":
        system_root = os.environ.get("SystemRoot")
        if system_root is not None:
            environment["SystemRoot"] = system_root
    args = [
        str(executable),
        "--no-pager",
        "--no-optional-locks",
        "--no-lazy-fetch",
        "--no-replace-objects",
        "--git-dir=" + str(root / ".git"),
        "--work-tree=" + str(root),
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.untrackedCache=false",
        "-c",
        "core.preloadIndex=false",
        "-c",
        "core.attributesFile=" + os.devnull,
        "-c",
        "core.excludesFile=" + os.devnull,
        "-c",
        "core.quotePath=false",
        "-c",
        "color.ui=false",
        "-c",
        "status.submoduleSummary=false",
        "-c",
        "status.showStash=false",
        "-c",
        "maintenance.auto=false",
        "-c",
        "gc.auto=0",
        "-c",
        "protocol.allow=never",
    ]
    if command is GitCommand.INDEX:
        args.extend(["ls-files", "--stage", "-z"])
    else:
        args.extend(
            [
                "status",
                "--porcelain=v2",
                "--branch",
                "--no-ahead-behind",
                "--untracked-files=all",
                "--ignore-submodules=all",
                "--no-renames",
                "-z",
            ]
        )
    deadline = time.monotonic() + timeout
    try:
        process = subprocess.Popen(
            args,
            cwd=root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            bufsize=0,
        )
    except FileNotFoundError as error:
        raise GitError(GitFailure.UNAVAILABLE) from error
    except OSError as error:
        raise GitError(GitFailure.IO) from error
    assert process.stdout is not None and process.stderr is not None
    output = bytearray()
    diagnostic = bytearray()
    try:
        # CPython >=3.12 supports nonblocking pipes on Windows as well as POSIX.
        # No reader threads, unbounded communicate(), or output temporary files.
        streams = [process.stdout, process.stderr]
        buffers = [output, diagnostic]
        finished = [False, False]
        for stream in streams:
            os.set_blocking(stream.fileno(), False)
        while not all(finished) or process.poll() is None:
            if time.monotonic() >= deadline:
                raise GitError(GitFailure.TIMEOUT)
            progressed = False
            for number, stream in enumerate(streams):
                if finished[number]:
                    continue
                buffer = buffers[number]
                try:
                    chunk = os.read(
                        stream.fileno(), min(8192, output_limit + 1 - len(buffer))
                    )
                except BlockingIOError:
                    continue
                if not chunk:
                    finished[number] = True
                    continue
                progressed = True
                buffer.extend(chunk)
                if len(buffer) > output_limit:
                    raise GitError(GitFailure.OUTPUT_LIMIT)
            if not progressed:
                time.sleep(0.005)
    except OSError as error:
        raise GitError(GitFailure.IO) from error
    finally:
        try:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired as error:
            raise GitError(GitFailure.TIMEOUT) from error
        except OSError as error:
            raise GitError(GitFailure.IO) from error
        finally:
            process.stdout.close()
            process.stderr.close()
    if process.returncode != 0 or diagnostic:
        # Stderr is deliberately not included, even in chained exceptions.
        raise GitError(GitFailure.COMMAND, returncode=process.returncode)
    return bytes(output)
