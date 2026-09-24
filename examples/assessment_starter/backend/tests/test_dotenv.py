"""Startup loads a scoped .env without modifying process state."""

import importlib
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from assessment_starter.core.config import Settings
from assessment_starter.model import FixedModel
from assessment_starter.model_factory import make_model


def test_env_file_selects_ollama_and_does_not_mutate_environment(
    tmp_path: Path,
) -> None:
    path = tmp_path / ".env"
    path.write_text(
        "# local model\nMODEL_PROVIDER=ollama\nOLLAMA_MODEL= llama3\n"
        'OLLAMA_BASE_URL="http://localhost:11434"\nMODEL_TIMEOUT_SECONDS=10\n',
        encoding="utf-8-sig",
    )
    before = dict(os.environ)
    settings = Settings.from_startup(path, environment={})
    assert settings.model_provider == "ollama"
    assert settings.ollama_model == "llama3.2:latest"
    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.model_timeout_seconds == 120
    assert not isinstance(make_model(settings), FixedModel)
    assert dict(os.environ) == before


def test_shell_overrides_file(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text("MODEL_PROVIDER=ollama\nOLLAMA_MODEL=llama3\n", encoding="utf-8")
    assert (
        Settings.from_startup(path, {"MODEL_PROVIDER": "fixed"}).model_provider
        == "fixed"
    )


def test_missing_file_stays_offline(tmp_path: Path) -> None:
    assert Settings.from_startup(tmp_path / "missing", {}).model_provider == "fixed"


@pytest.mark.parametrize(
    "content",
    [
        "MODEL_PROVIDER=invalid",
        "MODEL_PROVIDER",
        "MODEL_PROVIDER=ollama\nOLLAMA_MODEL=",
    ],
)
def test_invalid_file_fails_startup(tmp_path: Path, content: str) -> None:
    path = tmp_path / ".env"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        Settings.from_startup(path, {})


def test_default_location_is_backend_not_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import assessment_starter.core.config as config

    backend = tmp_path / "backend"
    fake_module = backend / "src" / "assessment_starter" / "core" / "config.py"
    fake_module.parent.mkdir(parents=True)
    (backend / ".env").write_text(
        "MODEL_PROVIDER=ollama\nOLLAMA_MODEL=llama3\n", encoding="utf-8"
    )
    monkeypatch.setattr(config, "__file__", str(fake_module))
    monkeypatch.chdir(tmp_path)
    assert Settings.from_startup(environment={}).ollama_model == "llama3"


def test_server_entry_point_uses_startup_loader() -> None:
    import assessment_starter.main as main

    original = main.app
    try:
        with patch.object(
            Settings, "from_startup", return_value=Settings(title="Loaded from startup")
        ) as loader:
            importlib.reload(main)
        loader.assert_called_once_with()
        assert main.app.title == "Loaded from startup"
    finally:
        main.app = original
