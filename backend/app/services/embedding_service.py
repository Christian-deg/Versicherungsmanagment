"""Embedding-Service: Chunks erzeugen, embedden und lokal in SQLite ablegen.

Hinweis zur Speicher-Wahl: Ursprünglich kam ChromaDB zum Einsatz. Dessen native
Rust-Bindings (alle 1.x-Versionen) stürzen aber auf Windows bei jedem
Schreibvorgang mit einer Access Violation ab und reißen den Backend-Prozess mit;
die ältere 0.6.x-Linie ist auf Python >= 3.13 nicht installierbar (keine
chroma-hnswlib-Wheels). Für ein Single-User-Setup mit wenigen tausend Chunks ist
Brute-Force-Cosine-Similarity über numpy mehr als schnell genug und kommt ohne
native Abhängigkeiten aus.
"""
from __future__ import annotations

import base64
import logging
import sqlite3
from contextlib import closing
from functools import lru_cache
from pathlib import Path

import numpy as np
from openai import AsyncOpenAI

from app.config import settings

log = logging.getLogger(__name__)

CHUNK_SIZE_CHARS = 2000  # ~500 Tokens
CHUNK_OVERLAP = 200

_DB_FILENAME = "vectors.sqlite"


@lru_cache(maxsize=1)
def _client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.openai_api_key)


def _connect() -> sqlite3.Connection:
    """Öffnet die Vektor-DB und stellt das Schema sicher (eine Datei in vectordb_dir)."""
    settings.vectordb_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.vectordb_dir / _DB_FILENAME)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY,
            insurance_id INTEGER NOT NULL,
            document_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            embedding BLOB NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS ix_chunks_document ON chunks(document_id)")
    return conn


def chunk_text(text: str) -> list[str]:
    """Einfaches überlappendes Chunking (zeichenbasiert, keine externe Tokenizer-Abhängigkeit)."""
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE_CHARS
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - CHUNK_OVERLAP
    return chunks


async def embed_and_store(
    insurance_id: int,
    document_id: int,
    text: str,
) -> int:
    """Embedded Chunks und legt sie in der Vektor-DB ab. Gibt Anzahl Chunks zurück."""
    chunks = chunk_text(text)
    if not chunks:
        return 0

    resp = await _client().embeddings.create(
        model=settings.model_embedding,
        input=chunks,
    )
    embeddings = [item.embedding for item in resp.data]

    rows = [
        (
            f"doc{document_id}_chunk{i}",
            insurance_id,
            document_id,
            i,
            chunk,
            np.asarray(vec, dtype=np.float32).tobytes(),
        )
        for i, (chunk, vec) in enumerate(zip(chunks, embeddings, strict=True))
    ]
    # closing() schließt die Verbindung; das innere `conn` committet die Transaktion
    with closing(_connect()) as conn, conn:
        conn.executemany(
            "INSERT OR REPLACE INTO chunks (id, insurance_id, document_id, chunk_index, text, embedding) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
    log.info("Embedded %d Chunks für Dokument %d (insurance=%d)", len(chunks), document_id, insurance_id)
    return len(chunks)


async def search(query: str, n_results: int = 5) -> list[dict]:
    """Embedded eine Frage und sucht die ähnlichsten Chunks (Cosine-Distanz)."""
    if not query.strip():
        return []
    resp = await _client().embeddings.create(model=settings.model_embedding, input=[query])
    qvec = np.asarray(resp.data[0].embedding, dtype=np.float32)

    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT insurance_id, document_id, chunk_index, text, embedding FROM chunks"
        ).fetchall()
    if not rows:
        return []

    matrix = np.vstack([np.frombuffer(r[4], dtype=np.float32) for r in rows])
    if matrix.shape[1] != qvec.shape[0]:
        # Embedding-Modell wurde gewechselt — alte Vektoren passen nicht mehr
        log.warning(
            "Vektor-Dimensionen passen nicht (DB: %d, Query: %d) — Dokumente neu hochladen "
            "oder data/vectordb leeren",
            matrix.shape[1],
            qvec.shape[0],
        )
        return []

    norms = np.linalg.norm(matrix, axis=1) * np.linalg.norm(qvec)
    norms[norms == 0] = 1e-12
    distances = 1.0 - (matrix @ qvec) / norms

    top = np.argsort(distances)[:n_results]
    return [
        {
            "text": rows[i][3],
            "metadata": {
                "insurance_id": rows[i][0],
                "document_id": rows[i][1],
                "chunk_index": rows[i][2],
            },
            "distance": float(distances[i]),
        }
        for i in top
    ]


def delete_for_document(document_id: int) -> None:
    """Entfernt alle Chunks zu einem Dokument."""
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))


# Statischer OCR-Prompt — außerhalb der Funktion für Prompt-Caching (LLM01)
_OCR_PROMPT = (
    "Transkribiere den gesamten sichtbaren Text dieser Seite vollständig und wortgetreu. "
    "Antworte nur mit dem transkribierten Text, ohne Erläuterungen oder Kommentare."
)


async def ocr_document_text(stored_path: str) -> str:
    """Extrahiert Text aus einem Dokument via OpenAI Vision (OCR-Fallback).

    Wird verwendet wenn kein nativer Textlayer vorhanden ist (gescannte PDFs, Bilder).
    Verarbeitet max. 10 Seiten (durch read_document_image_bytes begrenzt).
    Je Seite max. 4000 Output-Tokens.
    """
    # Lazily importieren um Zirkularität zu vermeiden
    from app.services.storage_service import StorageError, read_document_image_bytes

    try:
        images = read_document_image_bytes(stored_path)
    except StorageError as e:
        log.warning("Vision-OCR: Dokument nicht lesbar (%s): %s", Path(stored_path).name, e)
        return ""

    if not images:
        return ""

    client = _client()
    pages: list[str] = []
    for i, img_bytes in enumerate(images):
        b64 = base64.b64encode(img_bytes).decode("ascii")
        try:
            resp = await client.chat.completions.create(
                model=settings.model_chat,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{b64}",
                                    "detail": "high",
                                },
                            },
                            {"type": "text", "text": _OCR_PROMPT},
                        ],
                    }
                ],
                max_tokens=4000,
            )
            text = (resp.choices[0].message.content or "").strip()
            if text:
                pages.append(f"[Seite {i + 1}]\n{text}")
        except Exception:  # noqa: BLE001
            log.warning("Vision-OCR fehlgeschlagen für Seite %d von '%s'", i + 1, Path(stored_path).name)

    return "\n\n".join(pages)
