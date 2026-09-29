"""Konfiguration via Pydantic Settings (liest aus Umgebungsvariablen / .env)."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # OpenAI — drei Modell-Stufen (siehe AGENTS.md "Modelle"):
    # document = Vision-Extraktion (Policen, Belegfotos), chat = Chat/RAG + Empfehlungen,
    # fast = kleine Hilfsaufgaben (Klassifizierung, Evaluator, Beleg-Textlayer, OCR)
    openai_api_key: str = ""
    model_document: str = "gpt-5.6-terra"
    model_chat: str = "gpt-5.6-terra"
    model_fast: str = "gpt-5.6-luna"
    # Achtung: Wechsel des Embedding-Modells macht den Vektorindex ungültig
    # (andere Dimension) → danach data/vectordb leeren und neu indizieren
    model_embedding: str = "text-embedding-3-small"
    # Reasoning-Aufwand für Reasoning-Modelle (gpt-5.x, o-Serie). Explizit gesetzt,
    # weil der Server-Default je Modell verschieden ist (gpt-5.4-mini: none,
    # gpt-5.6-*: medium) und Reasoning-Tokens gegen das Token-Limit zählen.
    reasoning_effort: Literal["none", "minimal", "low", "medium", "high"] = "low"

    # Web-Suche (RecommendationAgent) — ungültiger Wert schlägt beim Start fehl
    search_provider: Literal["serper", "brave"] = "serper"
    search_api_key: str = ""

    # Pushover
    pushover_user_key: str = ""
    pushover_app_token: str = ""

    # Storage
    data_dir: Path = Path("./data")
    max_upload_bytes: int = 80 * 1024 * 1024  # 80 MB (Versicherungsdokumente — oft viele Seiten)
    max_invoice_upload_bytes: int = 10 * 1024 * 1024  # 10 MB (Rechnungen/Belege)
    # Automatische Backups — bewusst außerhalb von data_dir: Docker mountet den
    # Ordner separat (BACKUP_HOST_DIR), idealerweise auf ein anderes Laufwerk/NAS
    backup_dir: Path = Path("./backups")

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
