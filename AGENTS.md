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
| **Strukturierte DB** | SQLite (SQLAlchemy + Alembic) |
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
[DocumentAnalysisAgent (gpt-5.4 Vision)] ◀──▶ [DocumentEvaluator]
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
[QAAgent (gpt-5.4-mini)] ──▶ chromadb_search → 3-5 relevante Chunks
                          ──▶ get_insurance_metadata
    │
    ▼
Antwort + Quellen
```

## Modelle

| Aufgabe | Modell |
|---|---|
| Dokumentenanalyse (Vision) | `gpt-5.4` |
| Q&A / Chat | `gpt-5.4-mini` |
| Empfehlungen | `gpt-5.4-mini` |
| Embeddings | `text-embedding-3-small` |

## Erlaubte Kategorien (Allowlist)

```
KFZ, Haftpflicht, Hausrat, Gebäude, Kranken, Zahnzusatz,
Unfall, Rechtsschutz, Leben, Reise, Tier, Sonstige
```

## Agenten

Alle Agenten folgen den Regeln aus `.claude/skills/agentic-systems/SKILL.md`:
- `temperature=0`, `max_tokens` explizit gesetzt
- Pydantic `output_type` zwingend
- Input-/Output-Guardrails (Allowlist + Sensitive-Info-Check auf Freitext-Feldern)
- Nutzerdaten als separater `<eingabe>`-Block, nie im System-Prompt
- Keine Secrets im LLM-Kontext
- Pfad-Traversal-Schutz, exakt gepinnte Abhängigkeiten

### 1. `DocumentAnalysisAgent` + `DocumentEvaluator`

| | |
|---|---|
| **Modell** | `gpt-5.4` (Vision) |
| **Aufgabe** | Versicherungsdaten aus PDF-Seiten/Fotos extrahieren |
| **Tools** | keine (reine Vision-Analyse) |
| **Input** | Image-Bytes + Original-Dateiname |
| **Output** | `VersicherungsExtraktion` |
| **Evaluator** | Eigener gpt-5.4-mini-Agent prüft fachlich, max. 3 Retries |

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
| **Modell** | `gpt-5.4-mini` |
| **Aufgabe** | Fragen zu gespeicherten Versicherungen beantworten |
| **Tools** | `chromadb_search(frage)`, `get_insurance_metadata(id)`, `list_insurances()` |
| **Input** | Nutzerfrage als Text |
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
| **Modell** | `gpt-5.4-mini` |
| **Aufgabe** | Versicherungen mit Referenzwerten vergleichen |
| **Tools** | `get_reference_values(kategorie)` |
| **Output** | `Empfehlung` |

```python
class Empfehlung(BaseModel):
    handlungsbedarf: Handlungsbedarf  # KEINER/PRUEFEN/HANDELN
    hinweis: str = Field(..., max_length=500)
    details: str = Field(..., max_length=1000)
```

### 4. `NotificationService` (kein LLM)

Reiner Python-Service, kein Agent. Wird täglich via APScheduler ausgelöst.

- Prüft Versicherungs- und Garantie-Abläufe in 90/30/7 Tagen
- Sendet HTTP POST an `https://api.pushover.net/1/messages.json`
- 7-Tage-Alarm: `priority=1` (Hochpriorität)
- 30/90-Tage-Alarm: `priority=0` (normal)
- Markiert gesendete Notifications in DB (kein Doppelversand)

## Sicherheits-Pflichten (aus SKILL.md)

| ID | Maßnahme |
|---|---|
| LLM01 | Prompt-Injection-Pattern-Check im Input-Guardrail |
| LLM02 | Sensitive-Info-Check auf Freitext-Feldern (`hinweise`, `antwort`) |
| LLM03 | `pyproject.toml` mit `==`-Pins, `uv.lock` committen |
| LLM04 | Magic-Bytes-Validierung, max. 10 MB pro Upload |
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
```
