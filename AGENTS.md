# Versicherungs-Assistent — Projektbeschreibung & Agentensystem

Eine self-hosted Web-Applikation zur Verwaltung von Versicherungen und Produktgarantien
mit KI-gestützter Dokumentenanalyse, RAG-basiertem Chat-Assistenten und Push-Benachrichtigungen.

## Projektüberblick

| Aspekt | Wert |
|---|---|
| **Nutzer** | Single-User (kein Login) |
| **Hosting** | Self-hosted via Docker Compose |
| **Frontend** | Vue.js 3 + Vuetify 3 (Desktop + Mobile responsive) |
| **Backend** | Python 3.13 + FastAPI + OpenAI Agents SDK |
| **Strukturierte DB** | SQLite (SQLAlchemy, leichte In-Code-Migrationen) |
| **Vektor-DB** | SQLite-Vektorstore (lokal, numpy-Cosine) |
| **Notifications** | Pushover API (Push aufs Handy) |
| **Package-Manager** | uv |

## Datenfluss

```
PDF/Foto Upload
    │
    ▼
[Magic-Bytes-Validierung + UUID-Speicherung]
    │
    ▼
[DocumentAnalysisAgent (Vision)] ◀──▶ [DocumentEvaluator]
    │
    ▼
[Review-Screen für Nutzer]
    │
    ▼
[SQLite-Insert] + [Embedding → Vektorindex-Chunks]
    │
    ▼
APScheduler (täglich) ──▶ [Pushover-Push aufs Handy]


Chat-Frage
    │
    ▼
[QAAgent] ──▶ chromadb_search → 3-5 relevante Chunks
                          ──▶ get_insurance_metadata
    │
    ▼
Antwort + Quellen
```

## Modelle

Drei Stufen, konfigurierbar über `.env` (Stand 09/2026):

| Stufe (`.env`) | Modell | Aufgaben |
|---|---|---|
| `MODEL_DOCUMENT` | `gpt-5.6-terra` | Policen-Analyse (Vision), Rechnungsfotos (Vision) |
| `MODEL_CHAT` | `gpt-5.6-terra` | Q&A-Chat (RAG), Empfehlungen |
| `MODEL_FAST` | `gpt-5.6-luna` | Klassifizierer, Evaluator, Rechnungs-Textlayer, Vision-OCR |
| `MODEL_EMBEDDING` | `text-embedding-3-large` (lokal) / `-small` (Default) | Embeddings |
| `REASONING_EFFORT` | `low` | Reasoning-Aufwand aller gpt-5.x-Aufrufe |

Wechsel des Embedding-Modells macht den Vektorindex ungültig (andere Dimension) →
`data/vectordb` leeren, danach Chat-Seite → „Suchindex prüfen“.
Nach jedem Modellwechsel: Smoke-Test (`python -m app.smoke_test`, siehe CLAUDE.md).

## Erlaubte Kategorien (Allowlist)

```
KFZ, Haftpflicht, Hausrat, Gebäude, Kranken, Zahnzusatz,
Unfall, Rechtsschutz, Leben, Reise, Tier, Geräteversicherung, Sonstige
```

## Agenten

Alle Agenten folgen den Regeln aus `.claude/skills/agentic-systems/SKILL.md`:
- `ModelSettings` immer über `app/agents/model_config.model_settings(model, max_tokens)`:
  - **Kein `temperature`** — gpt-5.x lehnt es ab (fehlgeschlagene API-Aufrufe).
    Determinismus kommt über `output_type` + strikte System-Prompts.
  - **Reasoning explizit** (`REASONING_EFFORT`): Reasoning-Tokens zählen gegen
    `max_tokens`; der Server-Default ist je Modell verschieden (gpt-5.6: medium).
  - **`max_tokens` mit Luft** (≥ 1000, Vision/Tools 2000–4000): ein abgeschnittenes
    JSON verwirft den GESAMTEN Output.
  - Direkte Chat-Completions: `chat_completion_limits()` (`max_completion_tokens`).
- Pydantic `output_type` zwingend; Freitextfelder per `field_validator(mode="before")`
  kürzen statt verwerfen
- **KI-Fehler nie verschlucken:** Endpoints liefern 502 mit
  `ki_fehler.melde_ki_fehler(e)` (z. B. „Guthaben aufgebraucht“ + Push), Logs mit Traceback
- Input-/Output-Guardrails (Allowlist + Sensitive-Info-Check auf Freitext-Feldern)
- Nutzerdaten als separater `<eingabe>`-Block, nie im System-Prompt
- Keine Secrets im LLM-Kontext
- Pfad-Traversal-Schutz, exakt gepinnte Abhängigkeiten

### 1. `DocumentAnalysisAgent` + `DocumentEvaluator`

| | |
|---|---|
| **Modell** | `MODEL_DOCUMENT` (Vision) |
| **Aufgabe** | Versicherungsdaten aus PDF-Seiten/Fotos extrahieren |
| **Tools** | keine (reine Vision-Analyse) |
| **Input** | Image-Bytes + Original-Dateiname |
| **Output** | `VersicherungsExtraktion` |
| **Evaluator** | Eigener `MODEL_FAST`-Agent prüft fachlich, max. 3 Retries |

```python
class VersicherungsExtraktion(BaseModel):
    versicherer: str = Field(..., max_length=100)
    kategorie: Kategorie  # Enum
    vertragsnummer: str = Field(..., max_length=50)
    start_date: date | None
    end_date: date | None
    praemie_eur: float | None = Field(None, ge=0, le=100000)
    zahlungsintervall: Zahlungsintervall  # Enum: monatlich, jährlich, ...
    konfidenz: Confidence  # HIGH/MEDIUM/LOW
    hinweise: str = Field(..., max_length=500)
```

### 2. `QAAgent` (RAG)

| | |
|---|---|
| **Modell** | `MODEL_CHAT` |
| **Aufgabe** | Fragen zu Versicherungen, Produkten/Garantien und Rechnungen beantworten |
| **Tools** | `chromadb_search(frage)`, `get_insurance_metadata(id)`, `list_insurances()`, `list_products()`, `web_search(query)` |
| **Input** | Nutzerfrage als Text (optional mit Gesprächsverlauf) |
| **Output** | `ChatAntwort` |

```python
class ChatAntwort(BaseModel):
    antwort: str = Field(..., max_length=2000)
    quellen: list[str] = Field(default_factory=list, max_length=10)
    konfidenz: Confidence
```

### 3. `RecommendationAgent`

| | |
|---|---|
| **Modell** | `MODEL_CHAT` |
| **Aufgabe** | Versicherungen ganzheitlich bewerten (Preis + Deckung) |
| **Tools** | `get_reference_values(kategorie)`, `get_versicherung_details(id)`, `web_search(query)` |
| **Output** | `Empfehlung` |

```python
class Empfehlung(BaseModel):
    handlungsbedarf: Handlungsbedarf  # KEINER/PRUEFEN/HANDELN
    hinweis: str = Field(..., max_length=500)
    details: str = Field(..., max_length=1000)
```

### 4. `InvoiceAnalysisAgent` (Rechnungen/Kaufbelege)

| | |
|---|---|
| **Modell** | Textlayer: `MODEL_FAST` · Vision: `MODEL_DOCUMENT` |
| **Aufgabe** | Kaufdatum, Betrag, Produktname, Garantiedauer aus Belegen extrahieren |
| **Ablauf** | PDF-Textlayer zuerst; liefert er weder Kaufdatum noch Betrag (Scanner-PDF) oder scheitert er → Vision; Ergebnisse werden zusammengeführt |
| **Output** | `InvoiceExtraction` (alle Felder optional) → Review-Dialog im Frontend |
| **Fehler** | Dauerhafte API-Fehler (Guthaben, Key, Modell) → 502 mit Klartext, kein Vision-Versuch |

Beim Speichern wird ein fehlendes Produkt-Kaufdatum aus der Rechnung übernommen.

### 5. `DocumentClassifier`

| | |
|---|---|
| **Modell** | `MODEL_FAST` (Textlayer, sonst Vision mit erster Seite) |
| **Aufgabe** | Upload als `versicherung` / `rechnung` / `unbekannt` einordnen |
| **Fehler** | Fail-open zu `unbekannt` (Nutzer wählt selbst), Fehler aber mit Traceback im Log |

### 6. `NotificationService` (kein LLM)

Reiner Python-Service, kein Agent. Wird täglich via APScheduler ausgelöst.

- Prüft Versicherungs- und Garantie-Abläufe in 90/30/7 Tagen
- Prüft Kündigungsfristen („kündbar bis", jährlich wiederkehrend) in 30/7 Tagen
- Sendet HTTP POST an `https://api.pushover.net/1/messages.json`
- 7-Tage-Alarm: `priority=1` (Hochpriorität)
- 30/90-Tage-Alarm: `priority=0` (normal)
- Dedupliziert über `(ref_type, ref_id, days_before, target_date)` — nach
  Vertragsverlängerung oder im Folgejahr startet automatisch ein neuer Warnzyklus
- `FAILED`-Sendungen werden bis 3 Tage nach Fälligkeit erneut versucht;
  veraltete Warnungen (Eintrag gelöscht/Datum geändert) werden verworfen

## Sicherheits-Pflichten (aus SKILL.md)

| ID | Maßnahme |
|---|---|
| LLM01 | Prompt-Injection-Pattern-Check im Input-Guardrail |
| LLM02 | Sensitive-Info-Check auf Freitext-Feldern (`hinweise`, `antwort`) |
| LLM03 | `pyproject.toml` mit `==`-Pins, `uv.lock` committen |
| LLM04 | Magic-Bytes-Validierung, max. 80 MB (Dokumente) / 10 MB (Rechnungen); Pixel-Deckel gegen PDF-Bomben |
| LLM05 | Allowlist-Validierung für `kategorie`, kein direktes Pfad-Konkatenieren |
| LLM06 | Minimale Tools, Schreiboperationen außerhalb des Agenten |
| LLM07 | System-Prompt enthält keine Secrets |
| LLM09 | Evaluator-Agent für DocumentAnalysisAgent, max. 3 Retries |
| LLM10 | `max_tokens` explizit, Retry-Limit |
| ASI02 | `pathlib.Path.resolve()` gegen `data/documents/` Basis |

## Verzeichnisstruktur

```
versicherungs_web_app/
├── AGENTS.md
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── api/         # REST-Router
│       ├── agents/      # OpenAI Agents SDK
│       ├── models/      # SQLAlchemy ORM
│       ├── schemas/     # Pydantic API-Schemas
│       ├── services/    # Embedding, Pushover, Storage
│       └── scheduler/   # APScheduler-Jobs
├── frontend/
│   ├── package.json
│   ├── Dockerfile
│   └── src/
│       ├── views/       # Dashboard, Upload, Chat, Calendar, Products
│       ├── components/
│       ├── stores/      # Pinia
│       └── router/
└── data/                # Docker-Volume
    ├── documents/{kategorie}/{versicherer}/{jahr}/
    ├── db/insurance.sqlite
    └── vectordb/        # SQLite-Vektorstore
```

## Konfiguration (.env)

```
OPENAI_API_KEY=sk-...
PUSHOVER_USER_KEY=...
PUSHOVER_APP_TOKEN=...
DATA_DIR=/app/data
LOG_LEVEL=INFO
MODEL_DOCUMENT=gpt-5.6-terra
MODEL_CHAT=gpt-5.6-terra
MODEL_FAST=gpt-5.6-luna
MODEL_EMBEDDING=text-embedding-3-large
REASONING_EFFORT=low
SEARCH_PROVIDER=serper
SEARCH_API_KEY=...
```
