# API-Dokumentation

## Überblick

Das Backend stellt eine REST-API unter dem Prefix `/api` bereit.

Basisbereiche:

- `/api/health`
- `/api/insurances`
- `/api/products`
- `/api/invoices`
- `/api/documents`
- `/api/chat`
- `/api/exports`

## Allgemeine Hinweise

- Content-Type für JSON-Requests: `application/json`
- Uploads verwenden `multipart/form-data`
- Responses sind JSON, außer bei Export-Endpunkten
- Es gibt keine Authentifizierung, da das Projekt als Single-User self-hosted ausgelegt ist

## Health

### `GET /api/health`

Zweck:
- einfacher Verfügbarkeitscheck

Beispiel-Response:

```json
{
  "status": "ok"
}
```

## Versicherungen

### `GET /api/insurances`

Liefert alle Versicherungen, sortiert nach Enddatum.

Response:
- Array aus `InsuranceRead`

### `POST /api/insurances`

Legt eine neue Versicherung an.

Request-Body:

```json
{
  "name": "Privathaftpflicht – Muster",
  "kategorie": "Haftpflicht",
  "versicherer": "Muster Versicherung",
  "vertragsnummer": "HP-12345",
  "start_date": "2025-01-01",
  "end_date": "2026-01-01",
  "praemie_eur": 72.5,
  "zahlungsintervall": "jährlich",
  "notes": "optional"
}
```

Response:
- `201 Created`
- Objekt vom Typ `InsuranceRead`

### `GET /api/insurances/{insurance_id}`

Liefert eine einzelne Versicherung.

Fehler:
- `404`, wenn die Versicherung nicht existiert

### `PUT /api/insurances/{insurance_id}`

Aktualisiert eine Versicherung vollständig.

Request-Body:
- gleiches Schema wie beim Anlegen

Fehler:
- `404`, wenn die Versicherung nicht existiert

### `DELETE /api/insurances/{insurance_id}`

Löscht eine Versicherung samt zugehöriger Dokumente. Dabei werden auch die
Dokumentdateien und die RAG-Embeddings (Vektorindex) entfernt; verknüpfte Produkte
verlieren ihre Verknüpfung (`linked_insurance_id` wird `null`).

Response:
- `204 No Content`

Fehler:
- `404`, wenn die Versicherung nicht existiert

### `GET /api/insurances/summary/financial`

Liefert eine Finanzzusammenfassung über alle Versicherungen.

Response-Beispiel:

```json
{
  "total_year_eur": 1200.0,
  "total_month_eur": 100.0,
  "by_category": {
    "Haftpflicht": 72.5,
    "KFZ": 1127.5
  }
}
```

Hinweis:
- `praemie_eur` wird im Backend als Betrag pro Zahlungsintervall interpretiert
- für die Jahreskosten wird nach Intervall hochgerechnet

## Produkte

### `GET /api/products`

Liefert alle Produkte, sortiert nach Garantieende.

Response:
- Array aus `ProductRead`

### `POST /api/products`

Legt ein neues Produkt an.

Request-Body:

```json
{
  "name": "Waschmaschine",
  "kategorie": "Haushalt",
  "purchase_date": "2025-03-01",
  "warranty_end": "2027-03-01",
  "linked_insurance_id": 1,
  "notes": "optional"
}
```

Response:
- `201 Created`
- Objekt vom Typ `ProductRead`

### `GET /api/products/{product_id}`

Liefert ein einzelnes Produkt.

Fehler:
- `404`, wenn das Produkt nicht existiert

### `PUT /api/products/{product_id}`

Aktualisiert ein Produkt vollständig.

### `DELETE /api/products/{product_id}`

Löscht ein Produkt samt **aller** zugehörigen Rechnungen (inklusive Dateien) —
unabhängig von deren Aufbewahrungsfrist. Gedacht als explizite Aktion, wenn das
Produkt entsorgt wird. Die Aufbewahrungsfrist schützt nur vor dem versehentlichen
Löschen einzelner Rechnungen über `/api/invoices`.

Response:
- `204 No Content`

Fehler:
- `404`, wenn das Produkt nicht existiert

### `GET /api/products/summary/warranty-status`

Liefert die Garantie-Ampel.

Response-Beispiel:

```json
{
  "green": 3,
  "yellow": 1,
  "red": 0,
  "expired": 2,
  "no_warranty": 4
}
```

## Rechnungen

Rechnungen gehören immer zu einem Produkt. Beim Upload wird automatisch eine
Aufbewahrungsfrist (`retain_until`) berechnet:
`max(Kaufdatum + 730 Tage, Garantieende des Produkts)`. Fehlt das Kaufdatum,
wird das Kaufdatum des Produkts verwendet, ersatzweise das heutige Datum.

### `POST /api/invoices/analyze`

Analysiert eine Rechnungsdatei per KI (ohne sie zu speichern) und gibt einen
Vorschlag für Kaufdatum, Betrag, Produktname und Notiz zurück. Bei PDFs mit
Textlayer wird der Text direkt analysiert, sonst per Vision-Modell. Schlägt die
Analyse fehl, kommen leere Felder zurück — der Upload erfolgt erst nach
Bestätigung über `POST /api/invoices`. Der `produkt_name` dient als Vorschlag
für die Direkt-Anlage eines neuen Produkts im Frontend.

Request:
- `multipart/form-data`
- `file` – Datei, Pflichtfeld (PDF/PNG/JPG, max. 10 MB)

Response-Beispiel:

```json
{
  "purchase_date": "2025-11-20",
  "amount_eur": 899.99,
  "produkt_name": "Samsung TV QLED",
  "notes": "MediaMarkt – Samsung TV"
}
```

Fehler:
- `400` bei Dateiproblemen

### `POST /api/invoices`

Lädt eine Rechnung für ein Produkt hoch.

Request:
- `multipart/form-data`
- `product_id` – Integer, Pflichtfeld
- `file` – Datei, Pflichtfeld
- `purchase_date` – optionales Datum (`YYYY-MM-DD`)
- `amount_eur` – optionaler Float, 0 bis 1.000.000
- `notes` – optionaler String, max. 2000

Unterstützt:
- PDF
- PNG
- JPG/JPEG

Maximalgröße:
- 10 MB (Rechnungen; Versicherungsdokumente bis 80 MB)

Response:
- `201 Created`
- Objekt vom Typ `InvoiceRead`

Fehler:
- `400` bei Dateiproblemen, ungültigem Kaufdatum, Betrag außerhalb des Bereichs oder zu langen Notizen
- `404`, wenn das Produkt nicht existiert

### `GET /api/invoices`

Liefert alle Rechnungen, optional gefiltert nach Produkt.

Query-Parameter:
- `product_id` – optionale Integer-ID

Sortierung:
- kürzeste Aufbewahrungsfrist zuerst (`retain_until` aufsteigend)
- bei gleicher Frist neueste Rechnungen oben (`purchase_date` absteigend)

Response:
- Array aus `InvoiceRead`

### `GET /api/invoices/{invoice_id}`

Liefert eine einzelne Rechnung.

Fehler:
- `404`, wenn die Rechnung nicht existiert

### `GET /api/invoices/{invoice_id}/download`

Liefert die gespeicherte Rechnungsdatei als Download (Content-Disposition:
attachment mit dem Original-Dateinamen).

Response:
- die Datei mit ihrem ursprünglichen MIME-Typ

Fehler:
- `404`, wenn die Rechnung nicht existiert
- `410`, wenn die Datei nicht mehr auf der Festplatte liegt

### `DELETE /api/invoices/{invoice_id}`

Löscht eine Rechnung samt gespeicherter Datei. Während der Aufbewahrungsfrist
ist das Löschen nur mit `?force=true` möglich (das Frontend verlangt dafür eine
explizite Bestätigung) — gedacht für versehentlich hochgeladene Dateien.

Query-Parameter:
- `force` – optionaler Boolean (Standard `false`): löscht auch bei laufender Frist

Response:
- `204 No Content`

Fehler:
- `404`, wenn die Rechnung nicht existiert
- `409`, solange `retain_until` in der Zukunft liegt und `force` nicht gesetzt ist

## Dokumente

### `POST /api/documents/classify`

Erkennt automatisch, ob ein Upload eine Versicherung oder eine Produktrechnung
ist (günstiger Vorab-Check: Mini-Modell, Textlayer bevorzugt, Vision nur mit der
ersten Seite). Die Datei wird dabei **nicht** gespeichert — das Frontend leitet
anhand des Ergebnisses in den passenden Ablauf weiter.

Request:
- `multipart/form-data`, Feldname `file` (PDF/PNG/JPG, max. 80 MB)

Response-Beispiel:

```json
{
  "typ": "rechnung",
  "begruendung": "Enthält Händlername, Artikelliste und Gesamtbetrag inkl. MwSt."
}
```

`typ` ist `"versicherung"`, `"rechnung"` oder `"unbekannt"` (bei Fehlern oder
unklaren Dokumenten — der Nutzer wählt dann selbst).

Fehler:
- `400` bei Dateiproblemen

### `POST /api/documents/upload`

Lädt ein PDF oder Bild hoch und startet die KI-Analyse.

Request:
- `multipart/form-data`
- Feldname: `file`

Unterstützt:
- PDF
- PNG
- JPG/JPEG

Maximalgröße:
- 80 MB

Response:
- `ExtractionPreview`

Beispiel-Response:

```json
{
  "versicherer": "Muster Versicherung",
  "kategorie": "Haftpflicht",
  "vertragsnummer": "HP-12345",
  "start_date": "2025-01-01",
  "end_date": "2026-01-01",
  "praemie_eur": 72.5,
  "zahlungsintervall": "jährlich",
  "konfidenz": "HIGH",
  "hinweise": "Dokument gut lesbar",
  "document_id": 7
}
```

Fehler:
- `400` bei Dateiproblemen (auch korrupte/nicht lesbare PDFs)
- `422`, wenn der Sicherheitsfilter das Dokument ablehnt
- `502` bei KI-Analysefehlern (generische Meldung, Details im Server-Log)

### `POST /api/documents/upload-extra`

Lädt ein weiteres Dokument **ohne** KI-Analyse hoch (für Multi-Dokument-Anlage).
Die zurückgegebene Dokument-ID wird beim Confirm über `extra_document_ids`
mit zugeordnet.

Request:
- `multipart/form-data`, Feldname `file` (PDF/PNG/JPG, max. 80 MB)

Response:
- `201`-artig `DocumentRead` (Dokument liegt zunächst unter `_incoming`)

### `POST /api/documents/confirm/{document_id}`

Bestätigt oder korrigiert die Extraktion und legt daraus eine Versicherung an.

Request-Body:
- `InsuranceCreate` plus optional `extra_document_ids` (Liste von IDs aus
  `POST /upload-extra`, werden derselben Versicherung zugeordnet)

Wirkung:

- legt einen Versicherungseintrag an
- ordnet das Dokument (und optionale Extra-Dokumente) final zu
- verschiebt die Dateien in den finalen Ablagepfad
- extrahiert die Volltexte (nativer Textlayer via PyMuPDF, Fallback: Vision-OCR)
  und schreibt Embeddings in den Vektorindex — **im Hintergrund nach der
  Response**, damit mehrseitige Scans keinen Request-Timeout verursachen

Fehler:
- `404`, wenn das Dokument nicht existiert
- `400`, wenn das Dokument bereits zugeordnet wurde
- `410`, wenn die Quelldatei nicht mehr vorhanden ist

### `GET /api/documents`

Listet Dokumente, optional gefiltert nach Versicherung (neueste zuerst).

Query-Parameter:
- `insurance_id` – optionale Integer-ID

Response:
- Array aus `DocumentRead`

### `POST /api/documents/attach/{insurance_id}`

Hängt ein weiteres Dokument an eine **bestehende** Versicherung an — gedacht für
jährlich neu eintreffende Unterlagen (Beitragsrechnung, aktualisierte Police).
Keine KI-Feldextraktion; das Dokument wird gespeichert und im Hintergrund
volltextindiziert (inkl. Vision-OCR-Fallback), sodass es im Chat auffindbar ist.

Request:
- `multipart/form-data`, Feldname `file` (PDF/PNG/JPG, max. 80 MB)

Response:
- `201 Created`, `DocumentRead`

Fehler:
- `404`, wenn die Versicherung nicht existiert
- `400` bei Dateiproblemen

### `DELETE /api/documents/{document_id}`

Löscht ein einzelnes Dokument samt Datei und Vektorindex-Einträgen.

Response:
- `204 No Content`

Fehler:
- `404`, wenn das Dokument nicht existiert

### `GET /api/documents/{insurance_id}/recommendation`

Liefert die **gespeicherte** Empfehlung einer Versicherung (ohne neue KI-Bewertung).

Response-Beispiel:

```json
{
  "handlungsbedarf": "pruefen",
  "hinweis": "Vergleich lohnt sich.",
  "details": "Die Prämie liegt im Verhältnis zum Referenzwert ...",
  "created_at": "2026-06-13T09:00:00+00:00"
}
```

Fehler:
- `404`, wenn die Versicherung nicht existiert **oder** noch keine Empfehlung erzeugt wurde

### `POST /api/documents/{insurance_id}/recommendation`

Erzeugt (oder erneuert) die Empfehlung und **speichert** sie. Der Empfehlungs-Agent
bewertet ganzheitlich: Jahresprämie vs. Marktdurchschnitt, Vertragsdetails aus dem
Dokumentvolltext (Deckungssumme, Selbstbehalt, Ausschlüsse — via Tool
`get_versicherung_details`) und aktuelle Marktinfos via Websuche. Empfehlungen
werden zusätzlich **wöchentlich vom Scheduler geprüft** und nach einem Jahr
automatisch neu bewertet.

Response: wie `GET` (inkl. `created_at`).

Fehler:
- `404`, wenn die Versicherung nicht existiert
- `502` bei KI-Fehlern oder wenn der Sicherheitsfilter die Empfehlung blockiert

## Chat

### `POST /api/chat`

Sendet eine Nutzerfrage an den QA-Agenten — optional mit dem bisherigen
Gesprächsverlauf, damit Folgefragen funktionieren („Und wann läuft die ab?").

Request-Body:

```json
{
  "frage": "Und wann läuft die ab?",
  "verlauf": [
    { "rolle": "user", "text": "Welche KFZ-Versicherung habe ich?" },
    { "rolle": "assistant", "text": "Du hast eine KFZ-Versicherung bei der Allianz." }
  ]
}
```

- `verlauf` ist optional (Standard: leer = Frage ohne Kontext)
- max. 30 Nachrichten, Rollen nur `user`/`assistant`, je max. 4000 Zeichen
- Der Verlauf wird nur pro Browser-Sitzung gehalten — beim erneuten Öffnen der
  Assistenten-Seite beginnt ein neuer Chat
- Der Prompt-Injection-Guardrail prüft Frage und Verlauf

Der Agent beantwortet Fragen zu:
- gespeicherten Stammdaten (Prämien, Laufzeiten, Versicherer)
- konkreten Vertragsbedingungen aus dem Dokumentvolltext (Selbstbehalt, Ausschlüsse,
  Deckungssummen u.ä.), sofern der Volltext beim Upload erfolgreich extrahiert wurde
- **aktueller Marktlage / Tarifen** via Websuche (`web_search`-Tool, nur allgemeine
  Marktinfos, niemals mit persönlichen Daten); setzt `SEARCH_API_KEY` in der `.env` voraus

Response-Beispiel:

```json
{
  "antwort": "Deine nächste Versicherung läuft am 01.01.2026 ab.",
  "quellen": ["Privathaftpflicht – Muster"],
  "konfidenz": "HIGH"
}
```

Fehler:
- `400`, wenn der Sicherheitsfilter die Anfrage ablehnt (z. B. Prompt-Injection-Muster)
- `502`, wenn der Chat-Agent fehlschlägt oder die Antwort blockiert wird (generische Meldung, Details im Server-Log)

## Exporte

### `GET /api/exports/insurances.xlsx`

Exportiert alle Versicherungen als Excel-Datei.

Response:
- MIME: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

### `GET /api/exports/insurances.pdf`

Exportiert alle Versicherungen als PDF-Datei.

Response:
- MIME: `application/pdf`

### `GET /api/exports/products.xlsx`

Exportiert alle Produkte als Excel-Datei.

Response:
- MIME: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

## Datenmodelle

### `InsuranceCreate`

Felder:

- `name` – String, max. 200
- `kategorie` – Enum aus der Allowlist
- `versicherer` – String, max. 100
- `vertragsnummer` – String, max. 50
- `start_date` – optionales Datum
- `end_date` – optionales Datum
- `praemie_eur` – optionaler Float, 0 bis 100000
- `zahlungsintervall` – Enum
- `kuendigung_bis_tag` / `kuendigung_bis_monat` – optionales wiederkehrendes Datum
  (Tag 1–31, Monat 1–12, ohne Jahr): bis wann jährlich gekündigt werden kann.
  Tag und Monat müssen paarweise angegeben werden; unmögliche Kombinationen
  (z. B. 31.02.) werden mit `422` abgelehnt.
- `kuendigung_zum_tag` / `kuendigung_zum_monat` – optionales wiederkehrendes Datum:
  zu wann der Vertrag nach Kündigung endet. Gleiche Validierung wie oben.
- `notes` – optionaler String, max. 2000

### `InsuranceRead`

Wie `InsuranceCreate`, zusätzlich:

- `id`
- `created_at`

### `ProductCreate`

Felder:

- `name` – String, max. 200
- `kategorie` – freier String, max. 50
- `purchase_date` – optionales Datum
- `warranty_end` – optionales Datum
- `linked_insurance_id` – optionale Integer-ID; muss auf eine existierende Versicherung zeigen (sonst `400`)
- `notes` – optionaler String, max. 2000

### `ProductRead`

Wie `ProductCreate`, zusätzlich:

- `id`
- `created_at`

### `InvoiceCreate`

Felder:

- `purchase_date` – optionales Datum
- `amount_eur` – optionaler Float, 0 bis 1.000.000
- `notes` – optionaler String, max. 2000

Hinweis:
- beim Upload werden diese Felder als `multipart/form-data`-Formularfelder übergeben, nicht als JSON-Body

### `InvoiceRead`

Wie `InvoiceCreate`, zusätzlich:

- `id`
- `product_id`
- `original_filename`
- `mime_type`
- `retain_until` – berechnete Aufbewahrungsfrist
- `uploaded_at`

### `ExtractionPreview`

Rückgabe der Dokumentenanalyse:

- `versicherer`
- `kategorie`
- `vertragsnummer`
- `start_date`
- `end_date`
- `praemie_eur`
- `zahlungsintervall`
- `konfidenz`
- `hinweise`
- `document_id`

### `ChatRequest`

- `frage` – String, min. 1, max. 2000

### `ChatResponse`

- `antwort`
- `quellen`
- `konfidenz`

## Status- und Fehlercodes

Typische Codes:

- `200` – erfolgreicher Abruf
- `201` – erfolgreich angelegt
- `204` – erfolgreich gelöscht
- `400` – ungültige Nutzereingabe oder Dokumentzustand
- `404` – Ressource nicht gefunden
- `409` – Konflikt mit laufender Aufbewahrungsfrist (Rechnungen, Produkte)
- `410` – Datei nicht mehr vorhanden
- `502` – Fehler in KI-gestützter Verarbeitung

## Hinweise für Frontend-Integration

- Das Frontend nutzt Axios mit `baseURL: /api`
- Uploads benötigen `multipart/form-data`
- Exporte werden per Browser-Download direkt geöffnet
- Chat-, Dokument- und Empfehlungsergebnisse sollten immer auf Fehlertexte geprüft werden

## Ergänzende Dokumente

- `docs/BACKEND_DOKUMENTATION.md`
- `docs/FRONTEND_DOKUMENTATION.md`
- `docs/BEDIENUNGSANLEITUNG.md`
- `README.md`
