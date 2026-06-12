# Bedienungsanleitung

## Zweck der Anwendung

Der Versicherungs-Assistent hilft dabei, Versicherungen und Produktgarantien an einem Ort zu
verwalten. Dokumente können hochgeladen und automatisch analysiert werden. Zusätzlich unterstützt
ein Chat-Assistent bei Fragen zu gespeicherten Verträgen und Fristen.

## Start der Anwendung

### Mit Docker Compose

```bash
docker compose up -d --build
```

Anschließend ist das Frontend unter `http://localhost:8181` erreichbar.

### Lokale Entwicklung

Backend:

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Dann läuft das Frontend unter `http://localhost:5173`.

## Orientierung nach dem Öffnen

Nach dem Start zeigt die Anwendung links die Hauptnavigation:

- Dashboard
- Versicherungen
- Produkte / Garantien
- Kalender
- Dokument hochladen
- Assistent

Auf kleineren Bildschirmen öffnest du die Navigation über das Menü-Symbol oben links.

Zusätzlich gibt es oben den Schnellzugriff **Schnell hochladen**.

## Empfohlener Arbeitsablauf

Für den Einstieg ist dieser Ablauf sinnvoll:

1. Bestehende Police im Bereich **Dokument hochladen** hochladen
2. Erkannten KI-Vorschlag prüfen und ergänzen
3. Vertrag speichern
4. Verträge im Bereich **Versicherungen** prüfen
5. Garantien im Bereich **Produkte / Garantien** ergänzen
6. Fristen im **Dashboard** und **Kalender** überwachen
7. Detailfragen im Bereich **Assistent** stellen

## Bereich für Bereich erklärt

### 1. Dashboard verwenden

Das Dashboard ist die Startseite für den schnellen Überblick.

Hier siehst du:
- wie viele Versicherungen aktuell erfasst sind
- die monatlichen Gesamtkosten
- den nächsten bekannten Ablauf
- den Status vorhandener Garantien
- eine Übersicht der nächsten Fristen

Typische Nutzung:
- Prüfen, ob bald Verträge auslaufen
- Kostenentwicklung im Blick behalten
- direkt in Upload, Chat oder Kalender wechseln

### 2. Versicherung per Dokument erfassen

Öffne **Dokument hochladen**.

#### Schritt 1: Datei auswählen

Erlaubt sind:
- PDF
- PNG
- JPEG

Maximalgröße:
- 10 MB

#### Schritt 2: Analyse starten

Klicke auf **Hochladen & analysieren**.

Die Anwendung versucht unter anderem folgende Werte zu erkennen:
- Versicherer
- Kategorie
- Vertragsnummer
- Startdatum
- Enddatum
- Prämie
- Zahlungsintervall

#### Schritt 3: Vorschau prüfen

Nach der Analyse erscheint eine Extraktionsvorschau.

Prüfe besonders:
- Versicherer
- Kategorie
- Vertragsnummer
- Laufzeit
- Prämie

Du kannst alle angezeigten Felder manuell korrigieren.

#### Schritt 4: Speichern

Zum Speichern müssen mindestens diese Angaben vorhanden sein:
- Kategorie
- Versicherer
- Vertragsnummer
- Name

Klicke anschließend auf **Bestätigen & speichern**.

Nach dem Speichern wirst du automatisch zur Versicherungsübersicht weitergeleitet.

#### Vorgang abbrechen

Wenn der Vorschlag nicht passt, klicke auf **Verwerfen** und starte mit einer anderen Datei neu.

### 3. Versicherungen manuell anlegen und verwalten

Öffne **Versicherungen**.

#### Neue Versicherung anlegen

1. Klicke auf **Neu**
2. Fülle die Pflichtfelder aus:
   - Name
   - Kategorie
   - Versicherer
   - Vertragsnummer
3. Ergänze bei Bedarf:
   - Start
   - Ende
   - Prämie
   - Zahlungsintervall
   - Notizen
4. Klicke auf **Speichern**

#### Vorhandene Versicherung suchen

Nutze das Suchfeld, um nach folgenden Werten zu filtern:
- Name
- Kategorie
- Versicherer
- Vertragsnummer

#### Nach Status filtern

Über die Chips kannst du umschalten auf:
- **Alle**
- **Läuft bald ab**
- **Abgelaufen**

#### Versicherung bearbeiten

Klicke in der Tabelle auf das Stift-Symbol.

#### Empfehlung abrufen

Klicke auf das Glühbirnen-Symbol, um eine Empfehlung zum Vertrag zu öffnen.

#### Versicherung löschen

Klicke auf das Papierkorb-Symbol und bestätige den Löschdialog.

#### Export nutzen

Im Bereich **Versicherungen** stehen direkte Exporte zur Verfügung:
- **PDF**
- **Excel**

### 5. Rechnungen und Kaufbelege verwalten

Öffne **Rechnungen & Kaufbelege**.

Jede Rechnung gehört zu genau einem Produkt. Rechnungen werden als Garantienachweis aufbewahrt und
können erst nach Ablauf der Aufbewahrungsfrist gelöscht werden.

#### Rechnung hochladen

1. Klicke auf **Rechnung hochladen**
2. Wähle das zugehörige Produkt aus
3. Wähle die Datei aus (PDF, PNG oder JPEG, max. 10 MB)
4. Trage bei Bedarf Kaufdatum und Betrag ein
5. Klicke auf **Hochladen**

Die Aufbewahrungsfrist wird automatisch berechnet:
`max(Kaufdatum + 730 Tage, Garantieende des Produkts)`

#### Rechnungen filtern

Über die Chips kannst du umschalten auf:
- **Alle**
- **Demnächst fällig** (Aufbewahrungsfrist läuft bald ab)
- **Abgelaufen** (Rechnung kann gelöscht werden)

#### Rechnung löschen

Eine Rechnung kann erst gelöscht werden, wenn die Aufbewahrungsfrist abgelaufen ist.
Solange das Datum in der Zukunft liegt, wird ein Hinweis mit dem Fristende angezeigt.

### 5. Produkte und Garantien verwalten

#### Produkte suchen und filtern

Suche möglich nach:
- Produktname
- Kategorie
- verknüpfter Versicherung

Filter möglich nach:
- alle
- läuft bald ab
- abgelaufen

#### Produkt bearbeiten oder löschen

Nutze in der Tabelle das Stift- oder Papierkorb-Symbol.

Hinweis: Beim Löschen eines Produkts werden **alle zugehörigen Rechnungen mitgelöscht** —
unabhängig von deren Aufbewahrungsfrist.

#### Excel-Export

Die Produktübersicht bietet einen direkten Export nach Excel.

### 6. Kalender / Zeitstrahl lesen

Öffne **Kalender**.

Hier werden Versicherungen und Produkte gemeinsam auf einer Zeitachse angezeigt.

Der Kalender hilft dabei:
- Überschneidungen zu erkennen
- lange Laufzeiten zu vergleichen
- bald endende Garantien oder Verträge visuell schneller zu erfassen

Hinweis:
- Nur Einträge mit vollständigen Datumsangaben werden dargestellt.

### 7. Chat-Assistent verwenden

Öffne **Assistent**.

#### Frage stellen

Gib eine Frage in das Eingabefeld ein, zum Beispiel:
- Wann läuft meine nächste Versicherung ab?
- Welche Verträge kosten mich monatlich am meisten?
- Welche Produkte haben bald kein Garantieende mehr?
- Wie hoch ist mein Selbstbehalt bei der KFZ-Versicherung?
- Gilt meine Haftpflicht auch im Ausland?
- Was ist bei meiner Hausrat ausgeschlossen?

Der Assistent kann Fragen zu gespeicherten Stammdaten **und** zu konkreten Vertragsbedingungen
beantworten. Voraussetzung für Fragen zu Bedingungen ist, dass das Dokument beim Hochladen
einen lesbaren Textlayer hatte oder erfolgreich per OCR erkannt wurde.

Senden kannst du per:
- Klick auf das Sende-Symbol
- `Strg + Enter`
- `⌘ + Enter`

#### Beispiel-Fragen nutzen

Beim ersten Öffnen zeigt die Ansicht Beispiel-Fragen an. Ein Klick übernimmt die Frage ins Eingabefeld.

#### Antworten verstehen

Antworten enthalten je nach Ergebnis:
- die eigentliche Antwort
- Quellen-Chips
- eine Konfidenz-Angabe

Wenn ein Fehler auftritt, wird die Meldung direkt im Chatverlauf angezeigt.

## Bedeutung wichtiger Anzeigen

### Fristenfarben

Die Oberfläche nutzt Farblogik für Abläufe:

- **Grün** – ausreichend Restlaufzeit
- **Gelb** – nähert sich dem Ablauf
- **Rot** – kritisch oder sehr bald fällig
- **Grau** – kein Datum oder bereits abgelaufen, je nach Ansicht

### Konfidenz bei KI-Ergebnissen

Die Dokumentanalyse und der Chat können Konfidenzwerte anzeigen:

- **High** – hohe Sicherheit
- **Medium** – mittlere Sicherheit
- **Low** – geringe Sicherheit, bitte sorgfältig prüfen

## Typische Aufgaben

### Ich möchte meine erste Versicherung erfassen

1. Öffne **Dokument hochladen**
2. Lade die Police hoch
3. Prüfe die Vorschau
4. Speichere den Vertrag
5. Kontrolliere das Ergebnis unter **Versicherungen**

### Ich möchte ablaufende Verträge sehen

1. Öffne **Dashboard** für die Schnellübersicht
2. Öffne **Versicherungen** und filtere auf **Läuft bald ab**
3. Öffne **Kalender**, um die Zeiträume gemeinsam zu sehen

### Ich möchte eine Garantie für ein Produkt eintragen

1. Öffne **Produkte / Garantien**
2. Lege ein neues Produkt an
3. Trage Kaufdatum und Garantieende ein
4. Verknüpfe das Produkt optional mit einer Versicherung
5. Lade den Kaufbeleg unter **Rechnungen & Kaufbelege** hoch

### Ich möchte eine Frage an meine gespeicherten Daten stellen

1. Öffne **Assistent**
2. Formuliere deine Frage in Alltagssprache
3. Prüfe Antwort, Quellen und Konfidenz

## Fehlerbehebung

### Upload funktioniert nicht

Prüfe:
- ob die Datei PDF, PNG oder JPEG ist
- ob die Datei kleiner als 10 MB ist
- ob Backend und Frontend laufen

### Daten fehlen im Kalender

Prüfe:
- ob Start- und Enddatum bei Versicherungen eingetragen sind
- ob Kaufdatum und Garantieende bei Produkten hinterlegt sind

### Suche liefert kein Ergebnis

Prüfe:
- ob noch ein Statusfilter aktiv ist
- ob die Schreibweise im Suchfeld passt

### Chat liefert keine brauchbare Antwort

Prüfe:
- ob bereits Versicherungen oder Produkte gespeichert wurden
- ob die Frage konkret genug formuliert ist
- ob die Quellen zur Antwort angezeigt werden- ob das hochgeladene Dokument einen Textlayer enthielt (bei gescannten PDFs wird automatisch Vision-OCR verwendet; bei sehr schlechter Bildqualität kann die Erkennung unvollständig sein)
## Zusätzliche Dokumentation

Für technische Details und die Struktur des Frontends:

- `docs/FRONTEND_DOKUMENTATION.md`
- `README.md`
- `AGENTS.md`
