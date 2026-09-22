"""DocuMind CLI configuration: explicit environment-variable binding, no
hidden machine-specific defaults beyond the one documented local Ollama
convention (`http://localhost:11434`), mirroring `OllamaModelConfig`'s own
explicitness requirement (task SS13/SS44).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_BASE_URL = "http://localhost:11434"
_DEFAULT_CHAT_MODEL = "llama3.2"
_DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"
_DEFAULT_TIMEOUT_SECONDS = 60.0
_DEFAULT_INDEX_PATH = ".legoai-documind/index.sqlite3"
_DEFAULT_TENANT_ID = "local"


@dataclass(frozen=True, slots=True)
class DocuMindConfig:
    base_url: str
    chat_model: str
    embedding_model: str
    timeout_seconds: float
    index_path: Path
    tenant_id: str

    @staticmethod
    def from_environment() -> DocuMindConfig:
        return DocuMindConfig(
            base_url=os.environ.get(
                "LEGOAI_DOCUMIND_OLLAMA_BASE_URL", _DEFAULT_BASE_URL
            ),
            chat_model=os.environ.get(
                "LEGOAI_DOCUMIND_CHAT_MODEL", _DEFAULT_CHAT_MODEL
            ),
            embedding_model=os.environ.get(
                "LEGOAI_DOCUMIND_EMBEDDING_MODEL", _DEFAULT_EMBEDDING_MODEL
            ),
            timeout_seconds=float(
                os.environ.get(
                    "LEGOAI_DOCUMIND_TIMEOUT_SECONDS", str(_DEFAULT_TIMEOUT_SECONDS)
                )
            ),
            index_path=Path(
                os.environ.get("LEGOAI_DOCUMIND_INDEX_PATH", _DEFAULT_INDEX_PATH)
            ),
            tenant_id=os.environ.get("LEGOAI_DOCUMIND_TENANT_ID", _DEFAULT_TENANT_ID),
        )
