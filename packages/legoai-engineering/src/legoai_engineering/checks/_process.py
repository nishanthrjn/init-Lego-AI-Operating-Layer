"""Private bounded capture for trusted local check adapters on CPython 3.14."""

import os
import subprocess
import time
from pathlib import Path

from legoai_engineering.checks.errors import CheckError, CheckFailure
from legoai_engineering.checks.values import CheckPolicy


def _environment() -> dict[str, str]:
    # No global mutation or inherited tool flags, Python search paths or loaders.
    retained = (
        "SystemRoot",
        "WINDIR",
        "PATH",
        "TEMP",
        "TMP",
        "TMPDIR",
        "HOME",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
    )
    environment = {name: os.environ[name] for name in retained if name in os.environ}
    environment.update(
        {
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "NO_COLOR": "1",
        }
    )
    return environment


def _capture(
    executable: Path, arguments: list[str], root: Path, policy: CheckPolicy
) -> tuple[int, bytes, bytes]:
    deadline = time.monotonic() + policy.timeout_seconds
    try:
        process = subprocess.Popen(
            [str(executable), *arguments],
            cwd=root,
            env=_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            bufsize=0,
        )
    except FileNotFoundError as error:
        raise CheckError(CheckFailure.UNAVAILABLE) from error
    except OSError as error:
        raise CheckError(CheckFailure.IO) from error
    assert process.stdout is not None and process.stderr is not None
    streams = (process.stdout, process.stderr)
    buffers = (bytearray(), bytearray())
    finished = [False, False]
    try:
        # Supported for Windows pipes since CPython 3.12. No reader threads,
        # output spool files, or unbounded communicate() allocation.
        for stream in streams:
            os.set_blocking(stream.fileno(), False)
        while not all(finished) or process.poll() is None:
            if time.monotonic() >= deadline:
                raise CheckError(CheckFailure.TIMEOUT)
            progressed = False
            for index, stream in enumerate(streams):
                if finished[index]:
                    continue
                buffer = buffers[index]
                try:
                    chunk = os.read(
                        stream.fileno(),
                        min(8192, policy.max_output_bytes + 1 - len(buffer)),
                    )
                except BlockingIOError:
                    continue
                if not chunk:
                    finished[index] = True
                    continue
                progressed = True
                buffer.extend(chunk)
                if len(buffer) > policy.max_output_bytes:
                    raise CheckError(CheckFailure.OUTPUT_LIMIT)
            if not progressed:
                time.sleep(0.005)
    except OSError as error:
        raise CheckError(CheckFailure.IO) from error
    finally:
        try:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise CheckError(CheckFailure.CLEANUP) from error
        finally:
            process.stdout.close()
            process.stderr.close()
    assert process.returncode is not None
    return process.returncode, bytes(buffers[0]), bytes(buffers[1])
