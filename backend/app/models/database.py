"""SQLAlchemy DB-Setup."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
    echo=False,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    """Optimiert SQLite für WAL-Modus: bessere Lese-Parallelität, geringere Lock-Contention.

    - WAL: Write-Ahead Logging — Leser blockieren Schreiber nicht
    - synchronous=NORMAL: sicher bei WAL, reduziert fsync-Aufrufe
    - cache_size=-16000: 16 MB Page-Cache im RAM statt Standard-2MB
    - foreign_keys=ON: FK-Constraints erzwingen (SQLite ignoriert sie standardmäßig)
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=-16000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _migrate_db() -> None:
    """Führt einfache column-add Migrationen durch (kein Alembic nötig)."""
    new_columns = [
        ("kuendigung_bis_tag", "INTEGER"),
        ("kuendigung_bis_monat", "INTEGER"),
        ("kuendigung_zum_tag", "INTEGER"),
        ("kuendigung_zum_monat", "INTEGER"),
    ]
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(text("PRAGMA table_info(insurances)"))}
        for col, col_type in new_columns:
            if col not in existing:
                conn.execute(text(f"ALTER TABLE insurances ADD COLUMN {col} {col_type}"))
        conn.commit()


def init_db() -> None:
    """Erstellt alle Tabellen (für Single-User-Setup ausreichend, sonst Alembic)."""
    # Modelle importieren, damit metadata sie kennt
    from app.models import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_db()


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
