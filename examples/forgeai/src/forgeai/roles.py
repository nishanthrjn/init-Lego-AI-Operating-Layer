"""Pure closed operator role configuration; no file loading or authority."""

from dataclasses import dataclass, field


def label(value: object) -> str:
    """Bounded display identifiers, never terminal controls or absolute paths."""
    if (
        type(value) is not str
        or not 1 <= len(value) <= 128
        or not value[0].isalnum()
        or not value.isascii()
        or any(not (char.isalnum() or char in "-_.:/") for char in value)
        or ".." in value
        or ":/" in value
    ):
        raise ValueError("invalid role identifier")
    return value


@dataclass(frozen=True, slots=True)
class RoleModel:
    binding: str
    model: str
    url: str = field(default="http://127.0.0.1:11434", repr=False)
    timeout: float = 300.0
    replay: tuple[str, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        if self.binding not in ("replay", "ollama"):
            raise ValueError("role bindings must be local or replay")
        label(self.model)
        if (
            type(self.url) is not str
            or not self.url
            or any(not char.isprintable() or char.isspace() for char in self.url)
            or type(self.timeout) not in (int, float)
            or not 0 < self.timeout <= 3600
            or type(self.replay) is not tuple
            or any(type(path) is not str or not path.strip() for path in self.replay)
            or len(set(self.replay)) != len(self.replay)
        ):
            raise ValueError("invalid role settings")
        if self.binding == "replay":
            if not self.replay or self.model != "replay":
                raise ValueError("replay requires ordered files")
        elif self.replay:
            raise ValueError("Ollama cannot include replay files")


@dataclass(frozen=True, slots=True)
class RoleModels:
    revision: str
    coder: RoleModel
    reviewer: RoleModel

    def __post_init__(self) -> None:
        label(self.revision)
        if type(self.coder) is not RoleModel or type(self.reviewer) is not RoleModel:
            raise TypeError("both typed roles are required")


def parse_role(value: object) -> RoleModel:
    if type(value) is not dict:
        raise ValueError("role must be a table")
    if value.get("binding") == "replay":
        if set(value) != {"binding", "replay"} or type(value["replay"]) is not list:
            raise ValueError("replay requires only binding and files")
        return RoleModel("replay", "replay", replay=tuple(value["replay"]))
    if (
        value.get("binding") != "ollama"
        or not {"binding", "ollama_model"} <= set(value)
        or set(value) - {"binding", "ollama_model", "ollama_url", "ollama_timeout"}
    ):
        raise ValueError("unknown role binding or settings")
    return RoleModel(
        "ollama",
        value["ollama_model"],
        value.get("ollama_url", "http://127.0.0.1:11434"),
        value.get("ollama_timeout", 300.0),
    )


def parse_models(value: object) -> RoleModels:
    if (
        type(value) is not dict
        or set(value) != {"schema", "revision", "roles"}
        or value["schema"] != "forgeai-models/1"
        or type(value["roles"]) is not dict
        or set(value["roles"]) != {"coder", "reviewer"}
    ):
        raise ValueError("invalid models schema")
    return RoleModels(
        value["revision"],
        parse_role(value["roles"]["coder"]),
        parse_role(value["roles"]["reviewer"]),
    )
