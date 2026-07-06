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
    new_columns: dict[str, list[tuple[str, str]]] = {
        "insurances": [
            ("kuendigung_bis_tag", "INTEGER"),
            ("kuendigung_bis_monat", "INTEGER"),
            ("kuendigung_zum_tag", "INTEGER"),
            ("kuendigung_zum_monat", "INTEGER"),
            ("person", "VARCHAR(100)"),
        ],
        "notifications": [
            ("target_date", "DATE"),
        ],
        "products": [
            ("seriennummer", "VARCHAR(100)"),
            ("archived", "BOOLEAN NOT NULL DEFAULT 0"),
        ],
    }
    with engine.connect() as conn:
        for table, columns in new_columns.items():
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            for col, col_type in columns:
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
        # Backfill: bestehende Notifications auf das aktuelle Ablaufdatum beziehen,
        # damit die Deduplizierung nach dem Update keine Doppel-Warnungen erzeugt.
        conn.execute(
            text(
                "UPDATE notifications SET target_date = "
                "(SELECT end_date FROM insurances WHERE insurances.id = notifications.ref_id) "
                "WHERE ref_type = 'insurance' AND target_date IS NULL"
            )
        )
        conn.execute(
            text(
                "UPDATE notifications SET target_date = "
                "(SELECT warranty_end FROM products WHERE products.id = notifications.ref_id) "
                "WHERE ref_type = 'product' AND target_date IS NULL"
            )
        )
        # Prämien-Historie: Startwert für Bestandsverträge nachtragen (einmalig),
        # damit spätere Änderungen einen Bezugspunkt haben
        conn.execute(
            text(
                "INSERT INTO premium_history (insurance_id, praemie_eur, zahlungsintervall, changed_at) "
                "SELECT id, praemie_eur, zahlungsintervall, created_at FROM insurances "
                "WHERE id NOT IN (SELECT DISTINCT insurance_id FROM premium_history)"
            )
        )
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
