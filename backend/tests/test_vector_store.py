"""Tests für den SQLite-Vektorstore in embedding_service (ohne echte OpenAI-Calls)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services import embedding_service

# Deterministische Fake-Embeddings: Text → fester Vektor
_FAKE_VECTORS = {
    "kfz": [1.0, 0.0, 0.0, 0.0],
    "hausrat": [0.0, 1.0, 0.0, 0.0],
    "reise": [0.0, 0.0, 1.0, 0.0],
}


def _vector_for(text: str) -> list[float]:
    for key, vec in _FAKE_VECTORS.items():
        if key in text.lower():
            return vec
    return [0.0, 0.0, 0.0, 1.0]


def _fake_openai_client() -> MagicMock:
    async def fake_create(model: str, input: list[str] | str):  # noqa: A002
        texts = input if isinstance(input, list) else [input]
        return SimpleNamespace(data=[SimpleNamespace(embedding=_vector_for(t)) for t in texts])

    client = MagicMock()
    client.embeddings.create = fake_create
    return client


@pytest.fixture()
def vector_db(tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    return tmp_path


async def test_embed_search_delete_roundtrip(vector_db) -> None:
    with patch.object(embedding_service, "_client", return_value=_fake_openai_client()):
        n = await embedding_service.embed_and_store(1, 10, "KFZ Police Allianz")
        assert n == 1
        await embedding_service.embed_and_store(2, 20, "Hausrat Vertrag HUK")

        hits = await embedding_service.search("kfz versicherung", n_results=2)
        assert len(hits) == 2
        # Der KFZ-Chunk muss am ähnlichsten sein (Distanz ~0)
        assert hits[0]["metadata"]["insurance_id"] == 1
        assert hits[0]["metadata"]["document_id"] == 10
        assert hits[0]["distance"] < 0.01
        assert hits[1]["distance"] > 0.5

        embedding_service.delete_for_document(10)
        hits = await embedding_service.search("kfz versicherung", n_results=5)
        assert all(h["metadata"]["document_id"] != 10 for h in hits)


async def test_search_empty_db_returns_empty(vector_db) -> None:
    with patch.object(embedding_service, "_client", return_value=_fake_openai_client()):
        assert await embedding_service.search("irgendwas") == []


async def test_texts_for_insurance(vector_db) -> None:
    """Liefert den zusammengeführten Volltext genau einer Versicherung, gekürzt."""
    with patch.object(embedding_service, "_client", return_value=_fake_openai_client()):
        await embedding_service.embed_and_store(1, 10, "KFZ Police Selbstbehalt 300 EUR")
        await embedding_service.embed_and_store(2, 20, "Hausrat Deckung 50000 EUR")

        text = embedding_service.texts_for_insurance(1)
        assert "KFZ Police" in text
        assert "Hausrat" not in text  # nur die angefragte Versicherung

        assert embedding_service.texts_for_insurance(999) == ""  # keine Dokumente
        assert len(embedding_service.texts_for_insurance(1, max_chars=5)) == 5


async def test_upsert_replaces_chunks(vector_db) -> None:
    """Erneutes Embedden desselben Dokuments überschreibt statt zu duplizieren."""
    with patch.object(embedding_service, "_client", return_value=_fake_openai_client()):
        await embedding_service.embed_and_store(1, 10, "KFZ Police")
        await embedding_service.embed_and_store(1, 10, "KFZ Police aktualisiert")
        hits = await embedding_service.search("kfz", n_results=10)
        assert len(hits) == 1
        assert hits[0]["text"] == "KFZ Police aktualisiert"


async def test_dimension_mismatch_returns_empty(vector_db) -> None:
    """Nach Modellwechsel (andere Dimension) gibt die Suche leer zurück statt zu crashen."""
    with patch.object(embedding_service, "_client", return_value=_fake_openai_client()):
        await embedding_service.embed_and_store(1, 10, "KFZ Police")

    async def fake_create_other_dim(model: str, input):  # noqa: A002
        return SimpleNamespace(data=[SimpleNamespace(embedding=[0.5] * 8)])

    client = MagicMock()
    client.embeddings.create = fake_create_other_dim
    with patch.object(embedding_service, "_client", return_value=client):
        assert await embedding_service.search("kfz") == []
