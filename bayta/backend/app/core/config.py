from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


def _read_version() -> str:
    version_file = REPO_ROOT / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "0.0.0-dev"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BAYTA_", env_file=".env", extra="ignore")

    # /var/lib/bayta on the Pi; ./var during development
    data_dir: Path = REPO_ROOT / "backend" / "var"
    host: str = "0.0.0.0"
    port: int = 8000
    version: str = _read_version()
    timezone: str = "America/New_York"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "db" / "bayta.sqlite3"

    @property
    def photos_dir(self) -> Path:
        return self.data_dir / "photos"

    def ensure_dirs(self) -> None:
        for p in (self.data_dir, self.db_path.parent, self.photos_dir):
            p.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
