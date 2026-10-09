"""Prepared-image provenance under trusted composition, not hostile-Python attestation."""

from dataclasses import dataclass
from enum import Enum


class PreparationFailure(Enum):
    UNSUPPORTED_PROJECT = "unsupported_project"
    PYTHON_INCOMPATIBLE = "python_incompatible"
    LOCK_REQUIRED = "lock_required"
    LOCK_INVALID = "lock_invalid"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    PREPARATION_NETWORK_FAILED = "preparation_network_failed"
    PREPARATION_TOOL_FAILED = "preparation_tool_failed"
    PREPARATION_TIMEOUT = "preparation_timeout"
    PREPARED_IMAGE_UNAVAILABLE = "prepared_image_unavailable"
    PREPARED_IMAGE_IDENTITY_INVALID = "prepared_image_identity_invalid"


class PreparationError(Exception):
    def __init__(self, reason: PreparationFailure) -> None:
        if type(reason) is not PreparationFailure:
            raise TypeError("preparation failure requires PreparationFailure")
        self.reason = reason
        super().__init__(reason.value)


def _digest(value: str) -> bool:
    return (
        type(value) is str
        and value.startswith("sha256:")
        and len(value) == 71
        and all(c in "0123456789abcdef" for c in value[7:])
    )


@dataclass(frozen=True, slots=True, init=False)
class PreparedCheckEnvironment:
    """Minted only after preparation succeeds. No public image-string constructor.

    Private minting is a trusted-composition boundary, not a cryptographic seal.
    The image ID is authoritative; tags and repository metadata never select it.
    """

    base_image: str
    lock_digest: str
    manifest_digest: str
    image: str
    python: str
    profile: str

    def __init__(self) -> None:
        raise TypeError("use trusted Engineering prepare_check_environment")


def _mint(base: str, lock: str, manifest: str, image: str) -> PreparedCheckEnvironment:
    if not all(_digest(value) for value in (base, lock, manifest, image)):
        raise PreparationError(PreparationFailure.PREPARED_IMAGE_IDENTITY_INVALID)
    result = object.__new__(PreparedCheckEnvironment)
    for name, value in (
        ("base_image", base),
        ("lock_digest", lock),
        ("manifest_digest", manifest),
        ("image", image),
        ("python", "3.14.7"),
        ("profile", "uv-wheels-1"),
    ):
        object.__setattr__(result, name, value)
    return result
