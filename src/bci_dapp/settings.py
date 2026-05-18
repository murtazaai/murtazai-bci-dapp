"""Application settings loaded from environment variables.

Uses only the standard library - no mandatory dependency on pydantic-settings
or python-dotenv.  Swap the ``Settings`` body for a ``pydantic.BaseSettings``
subclass when richer validation is needed.

Usage::

    from bci_dapp.settings import settings

    agent = BCIAgent(base_url=settings.llm_base_url, model=settings.llm_model)

Copy ``.env.example`` to ``.env`` and fill in real values.  Never commit ``.env``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _env(key: str, default: str) -> str:
    """Return the value of env var *key*, or *default*."""
    return os.environ.get(key, default)


def _env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes"}


def _env_int(key: str, default: int) -> int:
    val = os.environ.get(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable application settings.

    All values can be overridden via environment variables.
    """

    # General
    app_name: str = field(default_factory=lambda: _env("APP_NAME", "murtazai-bci-dapp"))
    debug: bool = field(default_factory=lambda: _env_bool("APP_DEBUG", False))
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))

    # LLM / rig-core endpoint
    llm_base_url: str = field(
        default_factory=lambda: _env("LLM_BASE_URL", "https://api.openai.com/v1")
    )
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL", "gpt-4o-mini"))
    openai_api_key: str = field(default_factory=lambda: _env("OPENAI_API_KEY", ""))

    # EEG simulator
    eeg_sampling_rate: int = field(default_factory=lambda: _env_int("EEG_SAMPLING_RATE", 256))
    eeg_window_sec: float = field(default_factory=lambda: float(_env("EEG_WINDOW_SEC", "2.0")))

    # Ledger persistence
    ledger_path: str = field(default_factory=lambda: _env("LEDGER_PATH", "data/ledger.json"))


# Module-level singleton - import and use directly.
settings = Settings()
