"""Settings regression tests (Docker/env parsing)."""

from pathlib import Path

from app.core.config import Settings


def test_data_dir_default_is_anchored_to_repo_root():
    """Regression: a CWD-relative data dir made `cd backend && pytest` return 503."""
    settings = Settings()
    assert settings.data_dir.is_absolute()
    assert settings.data_dir == Path(__file__).resolve().parents[2] / "data"


def test_cors_origins_accepts_plain_env_string():
    """Regression: CORS_ORIGINS=http://localhost:5173 used to crash Settings."""
    settings = Settings(cors_origins="http://localhost:5173")
    assert settings.cors_origins_list == ["http://localhost:5173"]


def test_cors_origins_accepts_comma_separated_and_json():
    settings = Settings(cors_origins="http://a.test, http://b.test")
    assert settings.cors_origins_list == ["http://a.test", "http://b.test"]

    settings = Settings(cors_origins='["http://a.test", "http://b.test"]')
    assert settings.cors_origins_list == ["http://a.test", "http://b.test"]
