"""Konfiguration via Pydantic Settings (liest aus Umgebungsvariablen / .env)."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # OpenAI
    openai_api_key: str = ""
    model_document: str = "gpt-5.4"
    model_chat: str = "gpt-5.4-mini"
    model_embedding: str = "text-embedding-3-small"

    # Web-Suche (RecommendationAgent) — ungültiger Wert schlägt beim Start fehl
    search_provider: Literal["serper", "brave"] = "serper"
    search_api_key: str = ""

    # Pushover
    pushover_user_key: str = ""
    pushover_app_token: str = ""

    # Storage
    data_dir: Path = Path("./data")
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB

    # Logging
    log_level: str = "INFO"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @property
    def invoices_dir(self) -> Path:
        return self.data_dir / "invoices"

    @property
    def documents_dir(self) -> Path:
        return self.data_dir / "documents"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "db" / "insurance.sqlite"

    @property
    def vectordb_dir(self) -> Path:
        return self.data_dir / "vectordb"


settings = Settings()

# Verzeichnisse beim Import sicherstellen
for d in (settings.documents_dir, settings.invoices_dir, settings.db_path.parent, settings.vectordb_dir):
    d.mkdir(parents=True, exist_ok=True)
