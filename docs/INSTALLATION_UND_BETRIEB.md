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
- `data/invoices/` (Rechnungen/Kaufbelege)
- `data/db/insurance.sqlite` (+ `insurance.sqlite-wal`, `-shm` im laufenden Betrieb)
- `data/vectordb/`

### Backups

**Automatisch:** Das Backend erstellt täglich um 03:30 ein Komplett-Backup als ZIP
(Datenbank, Suchindex, alle Dokumente und Rechnungen) im Ordner `backups/` neben
`data/`. War der Rechner zur geplanten Zeit aus, wird das Backup kurz nach dem
nächsten Start nachgeholt. Jedes Archiv wird vor dem Speichern geprüft
(SQLite-Integritätscheck, CRC aller Dateien). Aufbewahrt werden das jüngste Backup
je Tag der letzten 7 Tage und je Monat der letzten 12 Monate. Schlägt ein Backup
fehl, kommt eine Pushover-Meldung, und das Dashboard zeigt eine Warnung.

Für Schutz vor Festplattenausfall den Backup-Ordner auf ein anderes Laufwerk, ein
NAS oder einen Cloud-Sync-Ordner legen — in `.env`:

```
BACKUP_HOST_DIR=D:/Backups/versicherung
```

danach `docker compose up -d`.

**Manuell:** Dashboard → **Backup** lädt dasselbe ZIP sofort herunter.

**Wiederherstellen:** Backend stoppen, Inhalt des ZIPs nach `data/` entpacken
(`db/`, `vectordb/`, `documents/`, `invoices/`), dabei alte
`insurance.sqlite-wal`/`-shm` löschen, Backend starten.

Zusätzlich sichern: `.env` (enthält die API-Schlüssel, liegt nicht im Backup).

> Nie nur `data/db/insurance.sqlite` kopieren: Im laufenden Betrieb liegen die
> neuesten Änderungen in `insurance.sqlite-wal`. Das Backend schreibt sie beim
> Start, beim Stoppen und nach jedem Backup in die Hauptdatei zurück — für
> Sicherungen trotzdem immer das Backup-ZIP verwenden.

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
- täglich 03:30 Uhr — Komplett-Backup nach `backups/` (siehe „Backups"), plus
  Nachholen kurz nach dem Start, wenn das letzte Backup älter als 20 Stunden ist
- wöchentlich (Mo 03:00) — Auffrischung von Empfehlungen, die älter als ein Jahr sind

War der Rechner zur geplanten Zeit im Standby, holt der Scheduler einen Job bis zu
6 Stunden später einmalig nach.

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

- Backups prüfen: Tooltip am **Backup**-Button im Dashboard zeigt das letzte
  automatische Backup; ab und zu ein ZIP testweise öffnen
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
