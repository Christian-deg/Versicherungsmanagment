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

Job:

- täglicher Notification-Check um 08:00 Uhr lokaler Zeit

Verarbeitung:

- Pending-Einträge für Versicherungen und Produkte erzeugen
- fällige Meldungen senden
- Versandstatus speichern

## Sicherheit im Betrieb

Wichtige Maßnahmen:

- keine Secrets in Quellcode oder Prompts eintragen
- `.env` nicht committen
- Datenverzeichnis gegen unbefugten Zugriff schützen
- Upload-Größenlimit bei 10 MB belassen oder bewusst ändern
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

- Backups prüfen
- Logs kontrollieren
- Pushover-Zustellung testen
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
- ob der Scheduler im Backend gestartet wurde

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
