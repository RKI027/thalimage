"""Tests for configuration loading."""

from pathlib import Path

import pytest

from thalimage.config import Settings


def test_default_paths() -> None:
    settings = Settings(data_dir=Path("/tmp/thalimage-test"))
    assert settings.resolved_db_path == Path("/tmp/thalimage-test/thalimage.db")
    assert settings.resolved_thumb_dir == Path("/tmp/thalimage-test/cache/thumbs")


def test_custom_db_path() -> None:
    settings = Settings(
        data_dir=Path("/tmp/thalimage-test"),
        db_path=Path("/custom/db.sqlite"),
    )
    assert settings.resolved_db_path == Path("/custom/db.sqlite")


def test_ensure_dirs(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "thal")
    settings.ensure_dirs()
    assert settings.data_dir.exists()
    assert settings.resolved_thumb_dir.exists()


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("THALIMAGE_PORT", "9999")
    monkeypatch.setenv("THALIMAGE_DEBUG", "true")
    settings = Settings()
    assert settings.port == 9999
    assert settings.debug is True


def test_default_host_is_loopback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("thalimage.config.default_data_dir", lambda: tmp_path)
    settings = Settings()
    assert settings.host == "127.0.0.1"


def test_cors_origins_default_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("thalimage.config.default_data_dir", lambda: tmp_path)
    settings = Settings()
    assert settings.cors_origins == []


def test_toml_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("thalimage.config.default_data_dir", lambda: tmp_path)
    (tmp_path / "config.toml").write_text('host = "127.0.0.1"\nport = 8123\n')
    settings = Settings()
    assert settings.host == "127.0.0.1"
    assert settings.port == 8123


def test_env_overrides_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("thalimage.config.default_data_dir", lambda: tmp_path)
    (tmp_path / "config.toml").write_text("port = 8123\n")
    monkeypatch.setenv("THALIMAGE_PORT", "9999")
    settings = Settings()
    assert settings.port == 9999
