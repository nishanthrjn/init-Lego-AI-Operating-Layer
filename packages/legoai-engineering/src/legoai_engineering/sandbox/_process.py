"""Private finite Docker CLI transport; no shell, threads or output spooling."""

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from legoai_engineering.sandbox.errors import SandboxError, SandboxFailure
from legoai_engineering.sandbox.ports import CancellationSignal


@dataclass(frozen=True, slots=True)
class _Cli:
    executable: Path
    config: Path

    def _run(
        self,
        arguments: list[str],
        deadline: float,
        limit: int = 65_536,
        cancellation: CancellationSignal | None = None,
        payload: bytes | None = None,
    ) -> tuple[int, bytes, bytes]:
        _check(deadline, cancellation)
        environment = {
            key: os.environ[key]
            for key in ("SystemRoot", "WINDIR")
            if key in os.environ
        }
        environment.update({"TEMP": str(self.config), "TMP": str(self.config)})
        try:
            process = subprocess.Popen(
                [
                    str(self.executable),
                    "--config",
                    str(self.config),
                    "--host",
                    "npipe:////./pipe/dockerDesktopLinuxEngine",
                    *arguments,
                ],
                cwd=self.config,
                env=environment,
                stdin=subprocess.PIPE if payload is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                bufsize=0,
            )
        except FileNotFoundError as error:
            raise SandboxError(SandboxFailure.RUNTIME_UNAVAILABLE) from error
        except OSError as error:
            raise SandboxError(SandboxFailure.CONTROL) from error
        assert process.stdout is not None and process.stderr is not None
        streams = (process.stdout, process.stderr)
        buffers = (bytearray(), bytearray())
        finished = [False, False]
        written = 0
        try:
            for stream in streams:
                os.set_blocking(stream.fileno(), False)
            if process.stdin is not None:
                os.set_blocking(process.stdin.fileno(), False)
            while not all(finished) or process.poll() is None:
                _check(deadline, cancellation)
                progressed = False
                if process.stdin is not None and not process.stdin.closed:
                    assert payload is not None
                    if written == len(payload):
                        process.stdin.close()
                    else:
                        try:
                            written += os.write(
                                process.stdin.fileno(),
                                payload[written : written + 8192],
                            )
                            progressed = True
                        except BlockingIOError:
                            pass
                        except BrokenPipeError:
                            process.stdin.close()
                for index, stream in enumerate(streams):
                    if finished[index]:
                        continue
                    buffer = buffers[index]
                    try:
                        chunk = os.read(
                            stream.fileno(), min(8192, limit + 1 - len(buffer))
                        )
                    except BlockingIOError:
                        continue
                    if not chunk:
                        finished[index] = True
                        continue
                    buffer.extend(chunk)
                    progressed = True
                    if len(buffer) > limit:
                        raise SandboxError(SandboxFailure.OUTPUT_LIMIT)
                if not progressed:
                    time.sleep(0.005)
        except OSError as error:
            raise SandboxError(SandboxFailure.CONTROL) from error
        finally:
            try:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired) as error:
                raise SandboxError(SandboxFailure.CLEANUP) from error
            finally:
                if process.stdin is not None:
                    process.stdin.close()
                process.stdout.close()
                process.stderr.close()
        assert process.returncode is not None
        if payload is not None and written != len(payload):
            raise SandboxError(SandboxFailure.PREPARATION)
        return process.returncode, bytes(buffers[0]), bytes(buffers[1])


def _check(deadline: float, cancellation: CancellationSignal | None) -> None:
    if cancellation is not None and cancellation.is_set():
        raise SandboxError(SandboxFailure.CANCELLED)
    if time.monotonic() >= deadline:
        raise SandboxError(SandboxFailure.TIMEOUT)
