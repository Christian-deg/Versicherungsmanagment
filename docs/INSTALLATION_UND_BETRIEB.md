# Installation und Betrieb

## Zweck

Dieses Dokument beschreibt die Einrichtung, Konfiguration und den laufenden Betrieb der
self-hosted Anwendung.

## Voraussetzungen

### Für Docker-Betrieb

- Docker
- Docker Compose
- gültiger OpenAI API Key

Optional für Push-Benachrichtigungen:

- Pushover-Konto
- User Key
- Application API Token

### Für lokale Entwicklung

- Python 3.13+
- `uv`
- Node.js / npm

## Konfiguration

Ausgangspunkt:

- `.env.example`

Vorgehen:

Im Repository-Hauptverzeichnis:

```bash
cp .env.example .env
```

Wichtige Variablen:

- `OPENAI_API_KEY`
- `PUSHOVER_USER_KEY`
- `PUSHOVER_APP_TOKEN`
- `DATA_DIR`
- `LOG_LEVEL`
- `MODEL_DOCUMENT`
- `MODEL_CHAT`
- `MODEL_EMBEDDING`

## Docker-Betrieb

### Starten

Im Repository-Hauptverzeichnis:

```bash
docker compose up -d --build
```

Erreichbarkeit:

- Frontend: `http://localhost:8181`
- Backend: intern im Compose-Netzwerk auf Port `8000`

### Container

Es werden zwei Services gestartet:

- `backend`
- `frontend`

### Datenpersistenz

Das Host-Verzeichnis `./data` wird in den Backend-Container nach `/app/data` gemountet.

Darin liegen:

- Dokumente
- SQLite-Datenbank
- Vektorindex-Daten (SQLite)

## Lokale Entwicklung

### Backend starten

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

### Frontend starten

```bash
cd frontend
npm install
npm run dev
```

Typische lokale URLs:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`

## Build, Lint und Tests

### Backend prüfen

```bash
cd backend
uv sync
uv run ruff check .
uv run pytest
```

### Frontend-Build prüfen

```bash
cd frontend
npm install
npm run build
```

## Betriebsverzeichnis

Im Datenverzeichnis werden die persistenten Dateien abgelegt:

- `data/documents/`
- `data/db/insurance.sqlite`
- `data/vectordb/`

### Empfehlung für Backups

Mindestens regelmäßig sichern:

- `.env`
- `data/db/insurance.sqlite`
- `data/vectordb/`
- `data/documents/`

## Pushover-Betrieb

Push-Benachrichtigungen funktionieren nur, wenn gesetzt sind:

- `PUSHOVER_USER_KEY`
- `PUSHOVER_APP_TOKEN`

Wenn diese Werte fehlen:

- startet die Anwendung trotzdem
- der tägliche Notification-Job überspringt den Versand
- im Log erscheint ein Hinweis

## Scheduler-Verhalten

Der APScheduler läuft im Backend-Prozess.

Jobs:

- täglich 08:00 Uhr lokaler Zeit — Notification-Check + Bereinigung verwaister Uploads
- wöchentlich (Mo 03:00) — Auffrischung von Empfehlungen, die älter als ein Jahr sind
- monatlich (1., 02:00 UTC) — konsistentes SQLite-Backup (Aufbewahrung 3 Monate)

Verarbeitung beim Notification-Check:

- Pending-Einträge erzeugen für:
  - Vertragsabläufe und Garantieenden (90/30/7 Tage vorher)
  - Kündigungsfristen „kündbar bis" (30/7 Tage vorher, jährlich wiederkehrend)
- veraltete Einträge (Vertrag gelöscht/Datum geändert) verwerfen
- fällige Meldungen senden; fehlgeschlagene Sendungen werden bis 3 Tage nach
  Fälligkeit erneut versucht
- Versandstatus speichern

## Sicherheit im Betrieb

Wichtige Maßnahmen:

- keine Secrets in Quellcode oder Prompts eintragen
- `.env` nicht committen
- Datenverzeichnis gegen unbefugten Zugriff schützen
- Upload-Größenlimits (80 MB Dokumente / 10 MB Rechnungen) belassen oder bewusst ändern
- nur erlaubte Dateitypen zulassen
- Reverse Proxy und TLS für externen Zugriff ergänzen

## Health-Check und Kontrolle

Für einen einfachen Servercheck:

- `GET /api/health`

Erwartete Antwort:

```json
{
  "status": "ok"
}
```

## Wartung

### Sinnvolle Regelaufgaben

- Backups prüfen (der Scheduler legt monatlich automatisch ein SQLite-Backup unter `data/db/` an)
- Logs kontrollieren
- Pushover-Zustellung testen
- Suchindex prüfen: im Assistenten den Button **Suchindex prüfen** ausführen
  (oder `POST /api/documents/maintenance/reindex`) — fehlende Dokumente werden
  automatisch nachindiziert
- API-Schlüssel auf Gültigkeit prüfen
- Abhängigkeiten und Modelle bei Bedarf aktualisieren

### Nach Änderungen prüfen

- Backend-Lint
- Backend-Tests
- Frontend-Build
- stichprobenartige UI-Prüfung

## Typische Störungen

### Frontend nicht erreichbar

Prüfen:

- ob der `frontend`-Container läuft
- ob Port `8181` frei ist
- ob der Build erfolgreich war

### Upload oder Chat funktioniert nicht

Prüfen:

- ob `OPENAI_API_KEY` gesetzt ist
- ob das Backend läuft
- ob externe API-Zugriffe möglich sind

### Keine Push-Benachrichtigungen

Prüfen:

- ob Pushover-Schlüssel gesetzt sind
- ob das Enddatum bzw. Garantieende korrekt erfasst wurde
- ob für Kündigungs-Warnungen die Felder „kündbar bis" (Tag + Monat) gepflegt sind
- ob der Scheduler im Backend gestartet wurde
- ob der Rechner/Container zur Trigger-Zeit (08:00) lief — verpasste Stufen
  werden beim nächsten Lauf innerhalb des Warnbands nachgeholt

### Daten fehlen nach Neustart

Prüfen:

- ob das `data/`-Verzeichnis korrekt gemountet ist
- ob versehentlich ohne persistentes Volume gestartet wurde

## Empfohlene Dokumente für den Betrieb

- `README.md`
- `docs/BACKEND_DOKUMENTATION.md`
- `docs/API_DOKUMENTATION.md`
- `docs/BEDIENUNGSANLEITUNG.md`
- `AGENTS.md`
