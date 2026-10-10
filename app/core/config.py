from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Configuración de la aplicación (variables de entorno / .env)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Faktu"
    app_version: str = "1.0.0"
    debug: bool = False
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    auto_create_tables: bool = True

    # Seguridad
    secret_key: str = "cambia-esta-clave-en-produccion-por-otra-segura-32b"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 días (app personal)

    # Base de datos
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'faktu.db'}"

    # Almacenamiento
    media_dir: Path = BASE_DIR / "media"
    max_upload_size: int = 10 * 1024 * 1024  # 10 MB

    # Valores por defecto del autónomo
    default_iva: float = 21.0
    default_irpf: float = 0.0

    @property
    def media_path(self) -> Path:
        return self.media_dir


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()