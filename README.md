# Versicherungs-Assistent

Self-hosted Web-App zur Verwaltung von Versicherungen und Produktgarantien mit
KI-gestützter Dokumentenanalyse, RAG-basiertem Chat und Push-Benachrichtigungen
via Pushover.

> ## ⚠️ Wichtiger Sicherheitshinweis
>
> Diese Anwendung ist **ausschließlich für den Betrieb im eigenen, lokalen
> Netzwerk** gedacht (Heimnetz / LAN). Sie darf **nicht direkt aus dem Internet
> erreichbar** gemacht werden:
>
> - Es gibt **keine Authentifizierung und keine Benutzerverwaltung** — jeder,
>   der die Web-Oberfläche erreichen kann, kann alle Daten lesen, ändern und
>   löschen sowie kostenpflichtige KI-Anfragen auslösen.
> - Die Anwendung ist **nicht gegen Angriffe aus dem Internet gehärtet**
>   (kein TLS, kein Rate-Limiting, kein CSRF-Schutz).
> - Wer sie dennoch entfernt erreichbar machen will, sollte sie hinter ein VPN
>   (z. B. WireGuard/Tailscale) oder einen Reverse-Proxy mit Authentifizierung
>   und TLS stellen — auf eigenes Risiko.

## Features

- 📄 **Dokumentenanalyse**: PDF/Foto hochladen → KI erkennt automatisch, ob es eine Versicherung
  oder eine Produktrechnung ist, und extrahiert die passenden Felder (Versicherer, Vertragsnummer,
  Laufzeit, Prämie bzw. Kaufdatum, Betrag, Produktname); bei Rechnungen kann das Produkt direkt
  mit angelegt werden (Rechnungen bis 80 MB)
- 🤖 **Chat-Assistent**: Fragen beantworten via RAG über alle gespeicherten Dokumente
- 📅 **Kalender / Zeitstrahl**: alle Versicherungen + Garantien auf einen Blick
- 💰 **Finanzübersicht**: Kosten pro Monat, pro Kategorie, Gesamtkosten
- 🛡 **Produkte / Garantien**: Garantie-Ampel (grün/gelb/rot), Produkt-Detailseite mit
  Belegen und Restgarantie-Balken, Seriennummern, Archivieren statt Löschen
  (Belege bleiben erhalten), Garantiedauer wird aus dem Kaufbeleg gelesen
- 💎 **Warenwert-Übersicht**: Summe aller Belegbeträge als Abgleich mit der
  Hausrat-Deckungssumme
- 📲 **Pushover-Benachrichtigungen**: 90/30/7 Tage vor Ablauf, hohe Priorität bei <7 Tagen;
  zusätzlich 30/7 Tage vor jeder Kündigungsfrist („kündbar bis") — jährlich wiederkehrend
- 🗓 **Kalender-Abo (ICS)**: Abläufe, Garantieenden und Kündigungsfristen als Feed für
  Apple/Google Kalender & Co. (`/api/exports/calendar.ics`)
- 📤 **Export**: PDF & Excel
- 👁 **Dokument-Ansicht**: gespeicherte Policen direkt im Browser öffnen
- 🌙 **Dark Mode**: umschaltbar, folgt standardmäßig der System-Einstellung
- 📱 **Installierbar (PWA)**: per „Zum Startbildschirm hinzufügen" wie eine App aufs Handy
- 🔧 **Suchindex-Wartung**: Konsistenz-Check des Vektorindex per Klick im Assistenten;
  fehlende Dokumente werden automatisch nachindiziert
- 🩺 **Datenqualitäts-Check**: Warnhinweise bei Verträgen ohne Frist, Prämie oder Dokument —
  damit Erinnerungen nicht ins Leere laufen
- 🔁 **Duplikat-Erkennung**: erkennt beim Upload bereits vorhandene Vertragsnummern und bietet
  an, das Dokument an den Bestandsvertrag zu hängen (inkl. Übernahme von Laufzeit/Prämie)
- 🔔 **Erinnerungs-Verlauf & Test-Push**: alle gesendeten Warnungen nachvollziehbar in der UI,
  Pushover-Konfiguration per Knopfdruck testbar
- 📄 **Vertrags-Detailseite**: Stammdaten, Fristen, Prämienverlauf, Dokumente und KI-Empfehlung
  je Vertrag auf einer Seite
- 📈 **Prämien-Historie**: Beitragsänderungen bleiben nachvollziehbar („+18 % seit 2024") und
  fließen in die KI-Empfehlung ein
- 🔎 **Globale Suche**: Verträge und Produkte direkt aus der Kopfleiste finden
- 👥 **Personen-Zuordnung**: „gehört zu"-Label je Vertrag mit Filter und Kosten je Person —
  Familien-Übersicht ohne Benutzerverwaltung
- 📉 **Kostenentwicklung**: Gesamt-Jahresprämie im Zeitverlauf auf dem Dashboard
- 💾 **Backup per Klick**: Komplett-Sicherung (Datenbank + Dokumente + Belege) als ZIP
- ↩️ **Lösch-Undo**: 5 Sekunden „Rückgängig" nach dem Löschen von Verträgen und Produkten
- 📷 **Kamera-Aufnahme**: Dokumente und Belege am Handy direkt abfotografieren
- 🌐 **Web-Suche (optional)**: aktuelle Marktinfos für den Empfehlungs-Agenten via Serper oder Brave
  (`SEARCH_PROVIDER`/`SEARCH_API_KEY` in `.env`); Suchanfragen werden auf sensible Daten geprüft,
  Treffer mit Injection-Mustern verworfen
- 🔒 **Sicherheit nach OWASP LLM Top 10**: Guardrails, Allowlists, Magic-Bytes-Validierung

## Tech-Stack

| Komponente | Technologie |
|---|---|
| Frontend | Vue 3 + Vuetify 3 + Vite |
| Backend | Python 3.13 + FastAPI |
| KI | OpenAI Agents SDK (gpt-5.4 / gpt-5.4-mini) |
| Strukturierte DB | SQLite + SQLAlchemy |
| Vektor-DB | SQLite-Vektorstore (lokal, numpy-Cosine) |
| Notifications | Pushover API |

## Quickstart

### 1. Pushover-Account einrichten
1. Account auf https://pushover.net/ anlegen, Pushover-App auf Handy installieren
2. **User Key** kopieren (von der Startseite)
3. Eine neue **Application** anlegen → **API Token** kopieren

### 2. `.env` anlegen
```bash
cp .env.example .env
# .env editieren: OPENAI_API_KEY, PUSHOVER_USER_KEY, PUSHOVER_APP_TOKEN
```

### 3. Mit Docker starten
```bash
docker compose up -d --build
```
Frontend: http://localhost:8080

### 4. Lokal entwickeln (ohne Docker)
**Backend:**
```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```
Dev-Frontend läuft auf http://localhost:5173 mit Proxy auf das Backend.

## Tests

```bash
cd backend
uv run pytest
```

## Architektur

Siehe `AGENTS.md` für eine detaillierte Beschreibung der Agenten,
Pydantic-Schemas und Sicherheitsmaßnahmen.

## Dokumentation

- `AGENTS.md` – technische Projekt-, Agenten- und Sicherheitsdokumentation
- `docs/FRONTEND_DOKUMENTATION.md` – detaillierte Beschreibung der aktuellen Frontend-Struktur, Navigation und UI-Abläufe
- `docs/BEDIENUNGSANLEITUNG.md` – Schritt-für-Schritt-Anleitung für die Bedienung der Anwendung
- `docs/BACKEND_DOKUMENTATION.md` – Aufbau des FastAPI-Backends, Services, Scheduler und Datenfluss
- `docs/API_DOKUMENTATION.md` – Übersicht aller REST-Endpunkte, Requests und Responses
- `docs/INSTALLATION_UND_BETRIEB.md` – Installation, Konfiguration, Docker-Betrieb und Wartung

## Verzeichnisstruktur

```
.
├── AGENTS.md                  # Projektbeschreibung & Agenten-Definitionen
├── docs/
│   ├── API_DOKUMENTATION.md
│   ├── BACKEND_DOKUMENTATION.md
│   ├── BEDIENUNGSANLEITUNG.md
│   ├── INSTALLATION_UND_BETRIEB.md
│   └── FRONTEND_DOKUMENTATION.md
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── api/
│       ├── agents/            # OpenAI Agents (Document, QA, Recommendation)
│       ├── models/
│       ├── schemas/
│       ├── services/          # Storage, Embedding, Pushover
│       └── scheduler/         # APScheduler-Notification-Job
├── frontend/
│   ├── package.json
│   ├── Dockerfile
│   ├── nginx.conf
│   └── src/
│       ├── views/             # Dashboard, Upload, Chat, Calendar, etc.
│       ├── api.js
│       └── App.vue
└── data/                      # Volume (gitignored)
    ├── documents/
    ├── db/
    └── vectordb/
```

## Sicherheit

Alle Agenten folgen einheitlichen Sicherheitsregeln (OWASP LLM Top 10, siehe `AGENTS.md`):
- `temperature=0`, `max_tokens` explizit
- Pydantic `output_type` zwingend
- Input-Guardrails: Prompt-Injection-Pattern-Erkennung
- Output-Guardrails: Allowlist + Sensitive-Info-Check
- Magic-Bytes-Validierung beim Upload (PDF/PNG/JPEG)
- Pfad-Traversal-Schutz via `pathlib.Path.resolve()`
- Keine Secrets im LLM-Kontext

## Zukünftige Features

- 🗄️ **ChromaDB-Migration**: Rückmigration zur ChromaDB, sobald Speicherprobleme auf diesem System behoben sind
- 🌐 **Sprachumschaltung Deutsch/Englisch**: umschaltbare Oberflächensprache (i18n, z. B. via
  vue-i18n) — UI-Texte, Datums-/Währungsformate und idealerweise auch die Antwortsprache des
  Chat-Assistenten folgen der gewählten Sprache

## Lizenz

Dieses Projekt steht unter der **GNU Affero General Public License v3.0 oder
später (AGPL-3.0-or-later)** — siehe [LICENSE](LICENSE).

Kurz zusammengefasst (ersetzt nicht den Lizenztext):

- Nutzung, Änderung und Weitergabe sind erlaubt.
- Abgeleitete Werke müssen ebenfalls unter der AGPL stehen.
- Wer eine veränderte Version als Netzwerkdienst betreibt, muss den Nutzern
  dieses Dienstes den Quellcode der veränderten Version zugänglich machen
  (AGPL § 13).
- Es gibt **keinerlei Gewährleistung** (AGPL §§ 15–16).
