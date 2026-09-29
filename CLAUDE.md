@AGENTS.md

# CLAUDE.md — Arbeitsnotizen für Claude Code

Ergänzt AGENTS.md (Architektur, Agenten, Sicherheitsregeln) um Befehle und Erkenntnisse
aus der Entwicklung. Der Skill `agentic-systems` ist generisch (Mistral, Airflow, loguru,
`temperature=0`) — wo er AGENTS.md widerspricht, gilt AGENTS.md.

## Befehle

| Zweck | Befehl |
|---|---|
| Backend-Tests | `cd backend && uv run pytest -q` |
| Lint | `cd backend && uv run ruff check app tests` |
| Frontend-Build | `cd frontend && npm run build` |
| App neu bauen + starten | `docker compose up -d --build` (UI: http://localhost:8181) |
| Backend-Logs | `docker logs versicherungs_backend --since 24h 2>&1 \| grep -iE "fehlgeschlagen\|Error"` |
| KI-Smoke-Test (echte API, wenige Cent) | `MSYS_NO_PATHCONV=1 docker exec versicherungs_backend /app/.venv/bin/python -m app.smoke_test` |

In Git-Bash ist `MSYS_NO_PATHCONV=1` bei `docker exec` nötig — sonst wird `/app/...` zu
`C:/Program Files/Git/app/...` umgeschrieben.

## Erkenntnisse

### KI-Fehler
- **Leere KI-Ergebnisse → zuerst die Backend-Logs prüfen.** Ursache war bisher ein
  verschluckter API-Fehler, nicht der Prompt (z. B. `429 insufficient_quota` /
  `credit_balance_exhausted` = OpenAI-Guthaben leer).
- KI-Fehler nie in leere Ergebnisse umwandeln: Endpoints antworten mit 502 und
  `ki_fehler.melde_ki_fehler(e)` (Klartext + Push bei leerem Guthaben); Logs mit Traceback.
- Die Unit-Tests mocken alle Agenten. Modellnamen, API-Parameter, Token-Limits und
  Guthaben prüft nur der Smoke-Test — nach jeder Modell- oder SDK-Änderung ausführen.

### gpt-5.x-Eigenheiten
- Kein `temperature` (Aufruf schlägt fehl).
- Reasoning-Tokens zählen gegen `max_tokens`/`max_output_tokens`. Der Server-Default ist je
  Modell verschieden (gpt-5.4-mini: none, gpt-5.6-*: medium) → Agenten-Einstellungen immer
  über `app/agents/model_config.model_settings()`, das den Aufwand explizit setzt.
- Chat Completions: `max_completion_tokens` statt `max_tokens` → `chat_completion_limits()`.
- Das Agents SDK kennt neue Modelle erst nach einem Update (`agents/models/default_models.py`);
  unsere Reasoning-Einstellung hängt davon bewusst nicht ab.
- Strukturierter Output: EIN ungültiges Feld (zu lang, abgeschnittenes JSON) verwirft das
  ganze Ergebnis → Freitextfelder per `field_validator(mode="before")` kürzen.
- Bilder an die API immer über `storage_service.image_data_url()` (echter MIME-Typ).

### Modelle aktualisieren
1. Verfügbare Modelle des Accounts auflisten — `models.list()` im Container, kostenlos:
   `MSYS_NO_PATHCONV=1 docker exec versicherungs_backend /app/.venv/bin/python -c "from openai import OpenAI; from app.config import settings; print(sorted(m.id for m in OpenAI(api_key=settings.openai_api_key).models.list() if m.id.startswith('gpt-5')))"`
2. Preise und Reasoning-Default je Modell: `https://developers.openai.com/api/docs/models/<modell>`.
3. `.env` (`MODEL_*`), Defaults in `backend/app/config.py`, `.env.example` und AGENTS.md
   „Modelle“ anpassen.
4. `docker compose up -d --build`, dann Smoke-Test — alle Checks müssen `OK` melden.
5. Embedding-Modell nur zusammen mit Neuindizierung wechseln (andere Vektordimension).

### Daten & Backups
- Tägliches Komplett-Backup: `services/backup_service.py` → `BACKUP_DIR` (Docker:
  `${BACKUP_HOST_DIR:-./backups}`). Status: `GET /api/exports/backup/status`.
- Nie nur `data/db/insurance.sqlite` kopieren — ohne `-wal` fehlten dort zeitweise
  Monate an Daten. `database.checkpoint_wal()` läuft bei Start, Stopp und nach jedem Backup.
- Dateien erst NACH `db.commit()` löschen (sonst Einträge ohne Datei bei Commit-Fehler).

### Umgebung (Windows)
- Dateien mit Umlauten nie per PowerShell `Get-Content`/`Set-Content` ersetzen (zerstört
  UTF-8) — Edit-Tool oder Python mit `encoding="utf-8"`.
- chromadb stürzt auf diesem System nativ ab → eigener SQLite-Vektorstore
  (`embedding_service.py`); nicht zurückwechseln.
- Bewusst ohne Login/Authentifizierung — die App ist nur fürs Heimnetz gedacht (README).
- `.claude/` ist gitignored; `CLAUDE.md` wird getrackt und landet im öffentlichen Mirror —
  keine privaten Daten oder Secrets eintragen.
