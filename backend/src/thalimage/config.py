"""Application configuration via pydantic-settings."""

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    from pydantic_settings import TomlConfigSettingsSource
except ImportError:
    TomlConfigSettingsSource = None  # type: ignore[assignment,misc]


def default_data_dir() -> Path:
    return Path.home() / ".thalimage"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="THALIMAGE_",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        file_secret_settings: Any,
    ) -> tuple[Any, ...]:
        sources: tuple[Any, ...] = (init_settings, env_settings, dotenv_settings, file_secret_settings)
        if TomlConfigSettingsSource is not None:
            toml_path = default_data_dir() / "config.toml"
            if toml_path.exists():
                sources = (
                    init_settings,
                    env_settings,
                    TomlConfigSettingsSource(settings_cls),
                    dotenv_settings,
                    file_secret_settings,
                )
        return sources

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    concurrent_scans: bool = True

    # Paths
    data_dir: Path = default_data_dir()
    db_path: Optional[Path] = None
    thumb_dir: Optional[Path] = None

    @property
    def resolved_db_path(self) -> Path:
        return self.db_path or (self.data_dir / "thalimage.db")

    @property
    def resolved_thumb_dir(self) -> Path:
        return self.thumb_dir or (self.data_dir / "cache" / "thumbs")

    def ensure_dirs(self) -> None:
        """Create data and cache directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.resolved_thumb_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
