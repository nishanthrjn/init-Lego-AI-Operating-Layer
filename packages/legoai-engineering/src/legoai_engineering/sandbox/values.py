"""Pure workload contracts, independent of the confinement backend."""

from dataclasses import dataclass, field

from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import RepositoryPath


def _bound(value: int, maximum: int) -> None:
    if type(value) is not int:
        raise TypeError("sandbox bound requires int")
    if not 1 <= value <= maximum:
        raise ValueError("sandbox bound outside supported range")


def _path(path: RepositoryPath) -> None:
    if type(path) is not RepositoryPath:
        raise TypeError("sandbox path requires RepositoryPath")
    path.value.encode("utf-8", "strict")
    if len(path.value.split("/")) > 32:
        raise ValueError("sandbox path depth exceeds supported range")
    if any(len(part.encode("utf-8")) > 255 for part in path.value.split("/")):
        raise ValueError("sandbox path component exceeds byte limit")
    excluded = {
        ".git",
        ".venv",
        ".ssh",
        ".aws",
        ".azure",
        ".docker",
        ".kube",
        ".gnupg",
        ".netrc",
        ".npmrc",
        ".pypirc",
        ".gitconfig",
        ".config",
        ".cache",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".env",
        "credentials",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        "__legoai__.py",
    }
    if any(part.casefold() in excluded for part in path.value.split("/")):
        raise ValueError("excluded sandbox path")


def _paths(paths: tuple[RepositoryPath, ...]) -> None:
    seen: set[str] = set()
    for path in paths:
        _path(path)
        key = path.value.casefold()
        if key in seen or any(
            key.startswith(other + "/") or other.startswith(key + "/")
            for other in seen
        ):
            raise ValueError("duplicate or overlapping sandbox paths")
        seen.add(key)


@dataclass(frozen=True, slots=True)
class SandboxRequest:
    """One Python script and explicit supplied text; never host access targets.

    Callers own selection/disclosure of contents. Filename exclusions cannot
    detect credentials embedded in otherwise ordinary source text.
    """

    script: str = field(repr=False)
    files: tuple[RepositoryText, ...] = field(default=(), repr=False)
    artifacts: tuple[RepositoryPath, ...] = ()

    def __post_init__(self) -> None:
        if type(self.script) is not str:
            raise TypeError("script requires str")
        if not 1 <= len(self.script.encode("utf-8")) <= 65_536:
            raise ValueError("script requires 1..65536 UTF-8 bytes")
        if "\0" in self.script:
            raise ValueError("script cannot contain NUL")
        if type(self.files) is not tuple or type(self.artifacts) is not tuple:
            raise TypeError("sandbox collections require tuples")
        if len(self.files) > 64 or len(self.artifacts) > 16:
            raise ValueError("sandbox file/artifact count exceeded")
        if any(type(item) is not RepositoryText for item in self.files):
            raise TypeError("inputs require RepositoryText")
        _paths(tuple(RepositoryPath(item.path) for item in self.files))
        _paths(self.artifacts)
        sizes = [len(item.text.encode("utf-8")) for item in self.files]
        if any(size > 262_144 for size in sizes) or sum(sizes) > 1_048_576:
            raise ValueError("sandbox input bytes exceeded")
        if any("\0" in item.text for item in self.files):
            raise ValueError("text inputs cannot contain NUL")


@dataclass(frozen=True, slots=True)
class SandboxPolicy:
    """Operator bounds; backend must reject unsupported confinement.

    Time covers preparation, execution and collection, excluding bounded cleanup.
    CPU/memory/PID/storage constraints are a fixed reference adapter profile.
    """

    timeout_seconds: int = 60
    max_output_bytes: int = 262_144
    max_artifact_bytes: int = 262_144
    max_total_artifact_bytes: int = 1_048_576

    def __post_init__(self) -> None:
        for value, ceiling in (
            (self.timeout_seconds, 300),
            (self.max_output_bytes, 1_048_576),
            (self.max_artifact_bytes, 1_048_576),
            (self.max_total_artifact_bytes, 4_194_304),
        ):
            _bound(value, ceiling)
        if self.max_artifact_bytes > self.max_total_artifact_bytes:
            raise ValueError("individual artifact bound exceeds total")


@dataclass(frozen=True, slots=True)
class SandboxArtifact:
    """Untrusted bytes, not a canonical Artifact or authorized mutation."""

    path: RepositoryPath
    content: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _path(self.path)
        if type(self.content) is not bytes:
            raise TypeError("artifact content requires bytes")
        if len(self.content) > 1_048_576:
            raise ValueError("artifact byte ceiling exceeded")


@dataclass(frozen=True, slots=True)
class SandboxResult:
    """Observed exit, bounded untrusted outputs; returned only after cleanup.

    Nonzero exit is a completed workload, not automatically infrastructure failure.
    An exit code alone does not prove why a workload failed.
    """

    exit_code: int
    stdout: bytes = field(repr=False)
    stderr: bytes = field(repr=False)
    artifacts: tuple[SandboxArtifact, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        if type(self.exit_code) is not int or not 0 <= self.exit_code <= 255:
            raise ValueError("container workload exit requires integer 0..255")
        for output in (self.stdout, self.stderr):
            if type(output) is not bytes:
                raise TypeError("sandbox output requires bytes")
            if len(output) > 1_048_576:
                raise ValueError("sandbox output ceiling exceeded")
        if type(self.artifacts) is not tuple:
            raise TypeError("artifacts require tuple")
        if len(self.artifacts) > 16 or any(
            type(item) is not SandboxArtifact for item in self.artifacts
        ):
            raise ValueError("invalid artifact collection")
        _paths(tuple(item.path for item in self.artifacts))
        if sum(len(item.content) for item in self.artifacts) > 4_194_304:
            raise ValueError("total artifact byte ceiling exceeded")
