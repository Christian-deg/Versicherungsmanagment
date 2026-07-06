# Backend-Dokumentation

## Zweck

Diese Datei beschreibt den Aufbau des Backends des Versicherungs-Assistenten. Sie ergänzt die
Projektübersicht aus `README.md` und die Agentenbeschreibung aus `AGENTS.md` um die konkrete
Serverstruktur, den Datenfluss, die Services und den Scheduler-Betrieb.

## Technische Basis

- Python 3.13+
- FastAPI
- SQLAlchemy
- SQLite
- OpenAI Agents SDK
- SQLite-Vektorstore (numpy-Cosine, keine nativen Abhängigkeiten)
- APScheduler
- ReportLab / OpenPyXL für Exporte

## Einstiegspunkt

Die Hauptanwendung befindet sich in:

- `backend/app/main.py`

Aufgaben der Hauptanwendung:

- Initialisierung der Datenbank beim Start
- Start und Stop des APScheduler-Lifecycles
- Registrierung aller Router unter `/api/*`
- Aktivierung der CORS-Middleware
- Bereitstellung des Health-Endpunkts `/api/health`

## Modulstruktur

### `app/api`

Enthält alle FastAPI-Router:

- `insurances.py`
- `products.py`
- `invoices.py`
- `documents.py`
- `chat.py`
- `notifications.py`
- `exports.py`

### `app/agents`

Enthält die KI-Komponenten:

- `document_agent.py` – Dokumentanalyse mit Vision + Evaluator
- `qa_agent.py` – RAG-gestützte Fragenbeantwortung
- `recommendation_agent.py` – Vergleich mit Referenzwerten
- `guardrails.py` – Input-/Output-Schutzlogik

### `app/models`

Enthält Datenbankmodell, Datenbankzugriff und Enums:

- `database.py`
- `models.py`
- `enums.py`

### `app/schemas`

Pydantic-Modelle für API-Requests und Responses.

### `app/services`

Nicht-UI-Funktionalität und technische Querschnittsdienste:

- `storage_service.py`
- `embedding_service.py`
- `pushover_service.py`
- `web_search_service.py`

### `app/scheduler`

Geplante Hintergrundaufgaben:

- `notification_job.py`

## Konfiguration

Die Konfiguration wird über `pydantic-settings` geladen.

Wichtige Variablen:

- `OPENAI_API_KEY`
- `PUSHOVER_USER_KEY`
- `PUSHOVER_APP_TOKEN`
- `DATA_DIR`
- `LOG_LEVEL`
- `MODEL_DOCUMENT`
- `MODEL_CHAT`
- `MODEL_EMBEDDING`

Wichtige abgeleitete Pfade:

- Dokumente: `data/documents/`
- SQLite: `data/db/insurance.sqlite`
- Vektorindex: `data/vectordb/vectors.sqlite`

Beim Import der Settings werden die benötigten Verzeichnisse automatisch angelegt.

## Lebenszyklus beim Start

Beim Start des FastAPI-Servers passiert Folgendes:

1. Logging wird initialisiert
2. Datenbanktabellen werden initialisiert
3. Scheduler für Benachrichtigungen wird gestartet
4. Router werden registriert
5. CORS wird aktiviert

Beim Shutdown:

1. Scheduler wird beendet
2. Anwendung beendet sich sauber

## Persistenzmodell

### Strukturierte Daten in SQLite

In SQLite werden insbesondere folgende Entitäten verwaltet:

- Versicherungen
- Produkte
- Dokumente
- Rechnungen
- Benachrichtigungen
- Prämienverlauf (`premium_history`: Startwert bei Anlage, neuer Eintrag bei
  jeder Änderung von Prämie/Zahlungsintervall — macht Beitragserhöhungen sichtbar)

Typische Inhalte:

- Versicherungs-Stammdaten
- Produkt- und Garantiedaten
- Dateipfade und KI-Zusammenfassungen
- Rechnungsdaten inkl. berechneter Aufbewahrungsfrist
- Notification-Status für Doppelversand-Schutz

Die Datenbank wird mit SQLite im WAL-Modus (Write-Ahead Logging) betrieben.
Dadurch können Lesezugriffe (FastAPI-Requests) und Schreibzugriffe (Scheduler)
ohne gegenseitige Blockierung parallel laufen. Zusätzlich sind `synchronous=NORMAL`,
`cache_size=-16000` (16 MB Page-Cache) und `foreign_keys=ON` als Pragmas gesetzt.

### Semantische Daten im SQLite-Vektorstore

Der SQLite-Vektorstore speichert:

- Text-Chunks aus bestätigten Versicherungsdokumenten
- Embeddings der Chunks
- Metadaten wie `insurance_id`, `document_id`, `chunk_index`

Jeder Chunk enthält neben den strukturierten Metafeldern (Versicherer, Prämie, Laufzeit)
auch den Volltext des Dokuments. Bei PDFs mit Textlayer wird dieser direkt via PyMuPDF
extrahiert. Bei gescannten PDFs oder Fotos erfolgt ein OCR-Fallback via OpenAI Vision
(`gpt-5.4-mini`, `detail=high`). Diese Daten werden vom QA-Agenten für semantische Suche
genutzt und ermöglichen Fragen zu konkreten Vertragsbedingungen.

## Zentrale Datenflüsse

### 1. Dokument-Upload bis gespeicherter Vertrag

1. Frontend lädt Datei nach `/api/documents/upload`
2. Backend validiert Dateigröße, Dateityp und Magic Bytes
3. Datei wird zunächst im `_incoming`-Bereich gespeichert
4. PDF oder Bild wird in analysierbare PNG-Bytes überführt
5. `DocumentAnalysisAgent` extrahiert strukturierte Versicherungsdaten (Vision); Dateiname wird vor der Übergabe sanitiert
6. `DocumentEvaluator` bewertet das Ergebnis, maximal 3 Retries
7. Vorschau wird an das Frontend zurückgegeben
8. Nutzer bestätigt oder korrigiert die Daten über `/api/documents/confirm/{document_id}`
9. Versicherung wird in SQLite angelegt
10. Datei wird in den finalen Dokumentenpfad verschoben
11. Volltext wird extrahiert: zuerst nativer Textlayer via PyMuPDF, bei leerem Ergebnis Vision-OCR als Fallback
12. Kombinierter Text (Metadaten + Volltext) wird gechunkt und in den Vektorindex eingebettet

### 2. Chat-Anfrage

1. Frontend sendet eine Frage an `/api/chat`
2. `QAAgent` nutzt zuerst seine Tools
3. `chromadb_search` liefert relevante Textstellen (inkl. Vertragsbedingungs-Volltext)
4. `list_insurances` oder `get_insurance_metadata` ergänzt strukturierte Daten
5. Agent erzeugt eine Antwort mit Quellen und Konfidenz
6. Ergebnis wird an das Frontend zurückgegeben

### 3. Empfehlung zu einem Vertrag

1. Frontend fordert Empfehlung für eine Versicherung an
2. Backend erstellt eine kurze strukturierte Zusammenfassung
3. `RecommendationAgent` ruft Referenzwerte zur Kategorie ab
4. Agent bewertet die Prämie relativ zum Durchschnitt
5. Ergebnis wird als strukturierte Empfehlung zurückgegeben

### 4. Tägliche Benachrichtigungen

1. Scheduler startet täglich um 08:00 Uhr lokaler Zeit
2. Fehlende Pending-Notifications werden erzeugt:
   - Vertragsabläufe und Garantieenden: Stufen 90/30/7 Tage
   - Kündigungsfristen („kündbar bis", jährlich wiederkehrend): Stufen 30/7 Tage
3. Veraltete Notifications (Vertrag gelöscht oder Datum geändert) werden verworfen
4. Fällige Notifications werden per Pushover versendet
5. Status wird auf `SENT` oder `FAILED` gesetzt; `FAILED` wird bis 3 Tage nach
   Fälligkeit erneut versucht

Deduplizierung: Schlüssel ist `(ref_type, ref_id, days_before, target_date)`.
`target_date` ist das konkrete Ablauf- bzw. Fristdatum — nach einer
Vertragsverlängerung (neues `end_date`) oder im Folgejahr (neue Kündigungs-
Deadline) startet dadurch automatisch ein neuer Warnzyklus.

### 5. Aktualisierung einer Versicherung

Beim `PUT /api/insurances/{id}` mit geänderten Feldern werden die RAG-Metadaten
aller zugehörigen Dokumente im Hintergrund neu eingebettet. Der bereits
extrahierte Volltext wird dabei aus den vorhandenen Chunks exakt rekonstruiert
(fester Chunk-Overlap) — es fällt kein erneutes OCR an.

## API-Bereiche

### Versicherungen

Zuständig für:

- Listen
- Anlegen
- Bearbeiten
- Löschen
- Finanzzusammenfassung (inkl. Aufteilung nach Kategorie und Person)
- Prämienverlauf (`GET /history/premiums`); die Prämienentwicklung fließt
  zusätzlich als Signal in die Empfehlungs-Zusammenfassung ein

Das Feld `person` („gehört zu") ist ein freies Familien-Label ohne
Benutzerverwaltung; es fließt in RAG-Metadaten und QA-Tools ein, damit der
Chat Fragen wie „welche Versicherungen gehören zu X?" beantworten kann.

### Produkte

Zuständig für:

- Listen
- Anlegen
- Bearbeiten (inkl. Seriennummer und Archiv-Status)
- Löschen
- Garantie-Ampel-Zusammenfassung (ohne archivierte Produkte)

Archivierte Produkte (verkauft/entsorgt) sind aus Ampel, Garantie-Warnungen
und ICS-Feed ausgenommen; ihre Belege bleiben bis zum Ende der
Aufbewahrungsfrist erhalten.

### Rechnungen

Zuständig für:

- Hochladen von Kaufbelegen (PDF/Bild) zu einem Produkt
- KI-Analyse (Kaufdatum, Betrag, Produktname, Garantiedauer in Monaten)
- Automatische Berechnung der Aufbewahrungsfrist
- Listen und Filtern nach Produkt
- Ansicht im Browser (`GET /{id}/file`, inline) und Download
- Löschen nach Ablauf der Aufbewahrungsfrist

### Dokumente

Zuständig für:

- Upload und Analyse
- Bestätigung der Extraktion
- Zuordnung eines analysierten Dokuments zu einem bestehenden Vertrag
  (`POST /assign/{id}`, Duplikat-Erkennung)
- Ansicht gespeicherter Dateien im Browser (`GET /{id}/file`, inline)
- Suchindex-Wartung (`POST /maintenance/reindex`): fehlende Dokumente werden
  im Hintergrund neu eingebettet
- Auslösen von Empfehlungen

### Chat

Zuständig für:

- Q&A mit RAG-Agent

### Erinnerungen

Zuständig für:

- Verlauf der Frist-Warnungen (`GET /api/notifications`)
- Pushover-Test (`POST /api/notifications/test`) — Konfigurationsfehler fallen
  sofort auf, nicht erst bei einer verpassten Frist

### Exporte

Zuständig für:

- Versicherungen als PDF
- Versicherungen als Excel
- Produkte als Excel
- ICS-Kalender-Feed (`calendar.ics`) mit Abläufen, Garantieenden und jährlich
  wiederkehrenden Kündigungsfristen — zum Abonnieren in Kalender-Apps
- Komplett-Backup (`backup.zip`): konsistente DB-Kopien (SQLite-Backup-API)
  plus alle Dokumente/Belege, ZIP_STORED für schnellen Export

## Agenten im Backend

### DocumentAnalysisAgent

Aufgabe:

- strukturierte Extraktion aus PDF-Seiten und Bildern

Besonderheiten:

- Vision-Eingabe als PNG-Bytes
- strukturierter Output via Pydantic
- Allowlist- und Sensitive-Info-Checks
- Evaluator mit maximal 3 Versuchen

### QAAgent

Aufgabe:

- Fragen ausschließlich auf Basis vorhandener Daten beantworten

Tools:

- `chromadb_search`
- `list_insurances`
- `get_insurance_metadata`

Besonderheiten:

- Tool-first-Verhalten
- keine Halluzinationen
- deutsche, knappe Antworten

### RecommendationAgent

Aufgabe:

- Einordnung einer Prämie relativ zu Referenzwerten

Tools:

- `get_reference_values`
- `web_search` (optional, für aktuelle Marktinformationen — erfordert `SEARCH_API_KEY`)

Besonderheiten:

- konservative, sachliche Empfehlung
- keine Nennung konkreter Konkurrenzangebote
- Web-Suche nur mit allgemeinen Begriffen, keine persönlichen Daten

## Storage-Service

Der Storage-Service übernimmt:

- Magic-Bytes-Validierung
- Größenlimit
- Dateitypprüfung
- sichere Dateispeicherung
- Pfad-Traversal-Schutz
- Auflösen gespeicherter Pfade gegen das aktuelle Datenverzeichnis
  (`resolve_stored_path`) — macht die Daten zwischen Docker (`/app/data/…`)
  und lokalem Betrieb portabel
- PDF-zu-Bild-Umwandlung für die Vision-Analyse (mit Pixel-Deckel von
  ~20 Megapixeln pro Seite als Schutz vor PDF-Dekompressions-Bomben)
- nativer PDF-Volltext-Extraktion (PyMuPDF `get_text()`)

### Sicherheitsrelevante Regeln

- maximal 80 MB pro Versicherungsdokument, 10 MB pro Rechnung
- erlaubte Typen: PDF, PNG, JPG, JPEG
- sichere Zielpfade unterhalb von `documents_dir` bzw. `invoices_dir`
- Dateinamen im Ziel mit UUID statt Originalname
- Dateiname wird vor der Übergabe an das LLM sanitiert (nur alphanumerisch + `._-`)

## Embedding-Service

Der Embedding-Service übernimmt:

- Zeichen-basiertes Chunking mit Überlappung
- Embedding-Erzeugung via OpenAI (`text-embedding-3-small`)
- Speicherung im Vektorindex (Chunks eines Dokuments werden atomar ersetzt —
  keine verwaisten Alt-Chunks beim Neu-Embedden)
- semantische Suche für Nutzerfragen
- Löschen aller Chunks zu einem Dokument
- Metadaten-Refresh nach Vertragsänderungen (`refresh_insurance_metadata`):
  rekonstruiert den Volltext aus vorhandenen Chunks und embedded mit
  aktualisiertem Metadaten-Block neu — ohne erneutes OCR
- Konsistenz-Check (`existing_document_ids`) für die Suchindex-Wartung
- Volltext-Obergrenze von 200.000 Zeichen je Dokument (Kostenschutz)
- Vision-OCR-Fallback: bei Dokumenten ohne nativen Textlayer werden die gerenderten
  PNG-Seiten via `gpt-5.4-mini` (Vision, `detail=high`) transkribiert; je Seite max.
  4000 Output-Tokens; Fehler einzelner Seiten werden abgefangen

Blockierende Arbeit (PDF-Rendering, Datei-I/O, SQLite-Zugriffe) läuft in
Threads (`anyio.to_thread`), damit der Event-Loop während großer Uploads
für Chat und Dashboard frei bleibt.

## Export-Service über Router

Die Exportfunktionen sind direkt im API-Router implementiert.

Unterstützte Formate:

- PDF für Versicherungen
- XLSX für Versicherungen
- XLSX für Produkte

Die Exporte werden als `StreamingResponse` ausgeliefert (ICS als `Response`
mit `text/calendar`).

## Scheduler und Notifications

Der Scheduler läuft im Backend-Prozess.

### Trigger

- täglich um 08:00 — Notifications berechnen und versenden, verwaiste Uploads bereinigen
- wöchentlich (Mo 03:00) — Empfehlungen auffrischen, die älter als ein Jahr sind
- monatlich (1., 02:00 UTC) — konsistentes SQLite-Backup (3 Monate Aufbewahrung)

### Benachrichtigungslogik

- Vertragsablauf / Garantieende: 90, 30 und 7 Tage vorher (je engste Stufe)
- Kündigungsfrist („kündbar bis"): 30 und 7 Tage vorher, jährlich wiederkehrend
- Deduplizierung über `(ref_type, ref_id, days_before, target_date)` —
  Verlängerungen und Folgejahre starten automatisch einen neuen Warnzyklus

### Prioritäten

- ≤7 Tage: hohe Priorität (Pushover priority=1)
- sonst: normale Priorität

### Fehlerverhalten

- Pushover-Konfigurationsfehler führen nicht zum kompletten Serverabbruch
- fehlerhafte Sends werden als `FAILED` markiert und bis 3 Tage nach
  Fälligkeit bei den nächsten Läufen erneut versucht
- erfolgreiche Sends werden als `SENT` markiert
- veraltete Warnungen (Eintrag gelöscht, Datum geändert) werden vor dem
  Versand erkannt und entfernt

## CORS

Standardmäßig freigegebene Origins:

- `http://localhost:5173`
- `http://localhost:3000`

Für Self-Hosting hinter Reverse Proxy sollte die Liste bei Bedarf angepasst werden.

## Logging

Das Backend nutzt Standard-Logging mit konfigurierbarem `LOG_LEVEL`.

Beispiele für geloggte Ereignisse:

- Start und Stop des Backends
- Start des Schedulers
- gespeicherte Dokumente
- erfolgreiche oder fehlgeschlagene Embeddings
- fehlgeschlagene Agentenläufe
- Fehler beim Notification-Versand

## Fehlerbehandlung

Typische Fehlerfälle:

- ungültige Datei oder Magic Bytes → `400`
- nicht gefundene Entität → `404`
- fehlende Quelldatei beim Confirm → `410`
- Fehler in KI-Analyse oder Chat → `502`

Das Backend behandelt diese Fälle über `HTTPException` und strukturierte Responses.

## Wartungshinweise

- Datenverzeichnis regelmäßig sichern
- SQLite-Datei und Vektorindex (data/vectordb) gemeinsam sichern
- `.env` mit gültigen API-Schlüsseln pflegen
- Logs auf fehlgeschlagene Notifications prüfen
- bei Modellwechseln Dokumentation und `.env.example` aktualisieren

## Ergänzende Dokumente

- `README.md`
- `AGENTS.md`
- `docs/API_DOKUMENTATION.md`
- `docs/INSTALLATION_UND_BETRIEB.md`
- `docs/FRONTEND_DOKUMENTATION.md`
