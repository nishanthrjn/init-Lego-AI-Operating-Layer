"""CTR-064 release-version subset; package versions have separate semantics."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, order=True)
class Version:
    """Exact release triple with lexicographic ordering, not compatibility.

    F1 admits releases only. Prereleases/ranges/text parsing are unsupported;
    no prerelease scheme or implicit 0.x compatibility is guessed.
    """

    major: int
    minor: int
    patch: int

    def __post_init__(self) -> None:
        for component in (self.major, self.minor, self.patch):
            if type(component) is not int:
                raise TypeError("version components must be integers")
            if component < 0:
                raise ValueError("version components must be nonnegative")
