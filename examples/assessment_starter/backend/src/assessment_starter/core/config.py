"""Validated startup settings; environment access is explicit."""

import math
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class Settings:
    title: str = "Assessment starter"
    model_provider: str = "fixed"
    ollama_model: str = ""
    ollama_base_url: str = field(default="http://127.0.0.1:11434", repr=False)
    model_timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if type(self.title) is not str or not self.title.strip():
            raise ValueError("A non-empty title is required")
        if self.model_provider not in ("fixed", "ollama"):
            raise ValueError("MODEL_PROVIDER must be fixed or ollama")
        if type(self.ollama_model) is not str:
            raise ValueError("OLLAMA_MODEL must be text")
        if self.model_provider == "ollama" and (
            not self.ollama_model.strip()
            or len(self.ollama_model) > 240
            or any(char.isspace() or ord(char) < 32 for char in self.ollama_model)
        ):
            raise ValueError("OLLAMA_MODEL must be a non-empty model name")
        try:
            self.ollama_model.encode("utf-8")
        except UnicodeError:
            raise ValueError("OLLAMA_MODEL must be valid UTF-8") from None
        if (
            type(self.model_timeout_seconds) not in (int, float)
            or not (0 < self.model_timeout_seconds <= 300)
            or not math.isfinite(self.model_timeout_seconds)
        ):
            raise ValueError("MODEL_TIMEOUT_SECONDS must be finite and within (0, 300]")
        try:
            self.ollama_base_url.encode("ascii")
            url = urlsplit(self.ollama_base_url)
            valid = (
                url.scheme in ("http", "https")
                and bool(url.hostname)
                and url.username is None
                and url.password is None
                and not url.query
                and not url.fragment
                and url.port != 0
                and not any(
                    char.isspace() or ord(char) < 32 for char in self.ollama_base_url
                )
            )
        except AttributeError, ValueError, UnicodeError:
            valid = False
        if not valid:
            raise ValueError(
                "OLLAMA_BASE_URL must be an HTTP(S) URL without credentials, query or fragment"
            )

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> Settings:
        values = os.environ if environment is None else environment
        try:
            timeout = float(values.get("MODEL_TIMEOUT_SECONDS", "10"))
        except ValueError:
            raise ValueError("MODEL_TIMEOUT_SECONDS must be numeric") from None
        return cls(
            model_provider=values.get("MODEL_PROVIDER", "fixed"),
            ollama_model=values.get("OLLAMA_MODEL", ""),
            ollama_base_url=values.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            model_timeout_seconds=timeout,
        )

    @classmethod
    def from_startup(
        cls,
        env_file: Path | None = None,
        environment: Mapping[str, str] | None = None,
    ) -> Settings:
        """Load backend/.env, then shell overrides; never mutate os.environ."""
        from dotenv import dotenv_values

        path = (
            env_file
            if env_file is not None
            else Path(__file__).resolve().parents[3] / ".env"
        )
        values: dict[str, str] = {}
        try:
            with path.open(encoding="utf-8-sig") as stream:
                parsed = dotenv_values(stream=stream, interpolate=False)
        except FileNotFoundError:
            parsed = {}
        for key, value in parsed.items():
            if key in {
                "MODEL_PROVIDER",
                "OLLAMA_MODEL",
                "OLLAMA_BASE_URL",
                "MODEL_TIMEOUT_SECONDS",
            }:
                if value is None:
                    raise ValueError(f"{key} requires a value in .env")
                values[key] = value
        values.update(os.environ if environment is None else environment)
        return cls.from_environment(values)
