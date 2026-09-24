"""Explicit immutable configuration; no environment reads."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    title: str = "Assessment starter"

    def __post_init__(self) -> None:
        if type(self.title) is not str or not self.title.strip():
            raise ValueError("A non-empty title is required")
