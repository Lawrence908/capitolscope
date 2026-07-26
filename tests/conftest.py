"""
Shared pytest fixtures and test-environment bootstrapping for CapitolScope.

IMPORTANT: The backend is imported with ``app/src`` as the import root
(e.g. ``from core.config import settings``), and ``core.config`` builds a
module-level ``settings`` object at import time that *requires* several
SUPABASE_* environment variables. Both concerns must be handled before any
test module imports app code, so they are done here at conftest import time
(pytest imports conftest.py before collecting test modules).
"""

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Make `app/src` the import root, exactly like PYTHONPATH=/app/src in Docker.
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
APP_SRC = REPO_ROOT / "app" / "src"
if str(APP_SRC) not in sys.path:
    sys.path.insert(0, str(APP_SRC))

# ---------------------------------------------------------------------------
# 2. Provide dummy required settings so `core.config` imports cleanly and no
#    test accidentally reaches a real Supabase/Redis/LLM endpoint. Only set a
#    var if the environment does not already define it, so a developer can
#    still point the integration suite at a real test database if they want.
# ---------------------------------------------------------------------------
_TEST_ENV_DEFAULTS = {
    "ENVIRONMENT": "testing",
    "TESTING": "true",
    "SUPABASE_URL": "https://testproject.supabase.co",
    "SUPABASE_KEY": "test-anon-key",
    "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
    "SUPABASE_PASSWORD": "test-db-password",
    "SUPABASE_JWT_SECRET": "test-jwt-secret",
    # Keep the optional local-LLM ticker reranker off so extract_ticker() never
    # makes a network call during tests.
    "CAPITOLSCOPE_TICKER_LLM_ENABLED": "false",
}
for _key, _value in _TEST_ENV_DEFAULTS.items():
    os.environ.setdefault(_key, _value)

import pytest  # noqa: E402  (import after sys.path / env setup, intentionally)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Absolute path to the repository root."""
    return REPO_ROOT


@pytest.fixture
def enhancer():
    """A fresh DataQualityEnhancer (heavy __init__ builds regex/mappings)."""
    from domains.congressional.data_quality import DataQualityEnhancer

    return DataQualityEnhancer()


@pytest.fixture
def ticker_extractor():
    """A fresh TickerExtractor with default company mappings loaded."""
    from domains.congressional.ticker_extraction import TickerExtractor

    return TickerExtractor()


@pytest.fixture
def make_settings(monkeypatch):
    """
    Factory that builds an isolated Settings instance.

    Values are applied through the *environment* (via monkeypatch, auto-undone
    per test) rather than init kwargs. This matters: ``SECRET_KEY`` declares
    ``AliasChoices(..., "SUPABASE_JWT_SECRET")``, and passing both that field
    and its alias as init kwargs trips an intermittent KeyError deep in
    pydantic-settings. The env source resolves alias choices correctly. Any
    pre-existing ``SECRET_KEY`` is cleared so tests that don't set it exercise
    the JWT-secret fallback deterministically. ``_env_file=None`` keeps the
    repo's real ``.env`` out of the picture.
    """
    from core.config import Settings

    def _make(**overrides):
        base = {
            "SUPABASE_URL": "https://testproject.supabase.co",
            "SUPABASE_KEY": "test-anon-key",
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
            "SUPABASE_PASSWORD": "test-db-password",
            "SUPABASE_JWT_SECRET": "test-jwt-secret",
        }
        base.update(overrides)
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        for key, value in base.items():
            monkeypatch.setenv(key, str(value))
        return Settings(_env_file=None)

    return _make
