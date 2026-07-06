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
- Rechnungen
- Kalender
- Erinnerungen
- Dokument hochladen
- Assistent

Auf kleineren Bildschirmen öffnest du die Navigation über das Menü-Symbol oben links.

Zusätzlich gibt es oben den Schnellzugriff **Schnell hochladen** und den
**Dark-Mode-Umschalter** (Mond-/Sonnen-Symbol). Beim ersten Besuch folgt das
Design automatisch der Einstellung deines Geräts; deine Wahl wird gespeichert.

In der oberen Leiste findest du außerdem die **globale Suche** (ab
Tablet-Breite): Tippe einen Vertrags- oder Produktnamen ein und spring mit
einem Klick direkt zur passenden Seite.

### App auf dem Handy installieren

Die Anwendung ist als Web-App installierbar:

- **Android (Chrome):** Menü → „App installieren" bzw. „Zum Startbildschirm hinzufügen"
- **iPhone/iPad (Safari):** Teilen-Symbol → „Zum Home-Bildschirm"

Danach startet sie mit eigenem Symbol im Vollbild wie eine normale App
(funktioniert nur, solange du im Heimnetz bist).

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
- die monatlichen Gesamtkosten (bei Personen-Labels auch je Person)
- den nächsten bekannten Ablauf
- den Status vorhandener Garantien und den erfassten Warenwert
- die **Kostenentwicklung** deiner Jahresprämien über die Zeit (sobald
  Prämienänderungen erfasst sind)
- eine Übersicht der nächsten Abläufe
- die nächsten **Kündigungsfristen** („kündbar bis") — damit du rechtzeitig
  kündigen oder wechseln kannst

Über den **Backup**-Button lädst du eine komplette Datensicherung als
ZIP-Datei herunter (Datenbank + alle Dokumente und Belege) — ideal, um sie
regelmäßig auf eine externe Platte oder in einen Cloud-Speicher zu legen.

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

Auf dem Handy kannst du mit **„Mit Kamera aufnehmen"** das Dokument direkt
abfotografieren (auch beim Rechnungs-Upload).

Maximalgröße:
- 80 MB (Versicherungsdokumente), Rechnungen bis 10 MB

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

**Duplikat-Hinweis:** Erkennt die Anwendung, dass die Vertragsnummer bereits zu
einem gespeicherten Vertrag gehört (typisch bei der jährlich neuen Police),
erscheint oben ein Hinweis mit zwei Möglichkeiten:

- **Anhängen + Laufzeit/Prämie aktualisieren** — das Dokument wird an den
  bestehenden Vertrag gehängt und Laufzeit, Prämie und Kündigungsdaten werden
  aus der Vorschau übernommen (empfohlen bei Vertragsverlängerung)
- **Nur Dokument anhängen** — der Vertrag bleibt unverändert

So entstehen keine doppelten Verträge. Du kannst den Hinweis auch ignorieren
und bewusst einen neuen Vertrag anlegen.

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

#### Datenlücken erkennen

Verträge mit unvollständigen Daten zeigen ein oranges Warnsymbol neben dem Namen
(bzw. Hinweiszeilen in der mobilen Ansicht). Gemeldet wird:

- keine Frist hinterlegt (weder Enddatum noch Kündigungsfrist) — es können
  **keine Erinnerungen** gesendet werden
- keine Prämie — der Vertrag fehlt in der Kostenübersicht
- kein Dokument — der Assistent kann nichts dazu finden

Das Dashboard fasst zusammen, wie viele Verträge betroffen sind.

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

#### Vertrags-Detailseite

Klicke auf den **Namen** eines Vertrags, um seine Detailseite zu öffnen. Dort
findest du alles auf einen Blick: Stammdaten, Restlaufzeit und Kündigungsfrist,
den **Prämienverlauf** als Zeitleiste, alle Dokumente (ansehen, ergänzen,
löschen) und die KI-Empfehlung mit „Neu bewerten". Über **„Frage zum Vertrag"**
springst du direkt in den Assistenten — mit vorbefülltem Bezug zum Vertrag
(gleiches gibt es auf der Produkt-Detailseite).

#### Verträge Personen zuordnen (Familie)

Im Bearbeiten-Formular gibt es das Feld **„Gehört zu"** — ein freies Label wie
„Christian" oder „Anna" (kein Login, nur eine Beschriftung). Sobald Labels
vergeben sind:
- erscheinen sie als **Filter-Chips** über der Vertragsliste
- steht die Person als Chip am Vertrag
- zeigt das Dashboard die **Kosten je Person**
- kann der Assistent Fragen wie „Welche Versicherungen gehören zu Anna?" beantworten

#### Versehentlich gelöscht? Rückgängig!

Nach dem Löschen eines Vertrags oder Produkts erscheint unten 5 Sekunden lang
eine Meldung mit **„Rückgängig"** — ein Klick stellt den Eintrag wieder her.
Erst danach wird endgültig gelöscht.

#### Versicherung bearbeiten

Klicke in der Tabelle auf das Stift-Symbol (oder auf der Detailseite auf
**Bearbeiten**).

In der Prämien-Spalte siehst du zusätzlich die Jahresprämie und den Anteil an
deinen Gesamtkosten (z. B. „311,00 € p.a. · 28 % der Gesamtkosten").

#### Beitragserhöhungen erkennen (Prämienverlauf)

Wenn du beim Bearbeiten die Prämie änderst (z. B. nach der jährlichen
Beitragsanpassung), merkt sich die Anwendung den alten Wert. In Liste und
Detailseite erscheint dann ein Trend-Chip wie **„+18 % seit 2024"** — rot bei
Erhöhungen, grün bei Senkungen. Die Entwicklung fließt auch in die
KI-Empfehlung ein.

#### Dokumente ansehen und ergänzen

Klicke auf das Büroklammer-Symbol. Im Dialog kannst du:
- vorhandene Dokumente **im Browser öffnen** (Symbol „in neuem Tab öffnen")
- neue Unterlagen anhängen, z. B. die jährliche Beitragsrechnung — sie werden
  automatisch für den Assistenten durchsuchbar gemacht
- einzelne Dokumente löschen

#### Empfehlung abrufen

Klicke auf das Glühbirnen-Symbol, um eine Empfehlung zum Vertrag zu öffnen.

#### Versicherung löschen

Klicke auf das Papierkorb-Symbol und bestätige den Löschdialog.

#### Export nutzen

Im Bereich **Versicherungen** stehen direkte Exporte zur Verfügung:
- **PDF**
- **Excel**

### 4. Rechnungen und Kaufbelege verwalten

Öffne **Rechnungen & Kaufbelege**.

Jede Rechnung gehört zu genau einem Produkt. Rechnungen werden als Garantienachweis aufbewahrt und
können erst nach Ablauf der Aufbewahrungsfrist gelöscht werden.

#### Rechnung hochladen

1. Klicke auf **Rechnung hochladen**
2. Wähle die Datei aus (PDF, PNG oder JPEG, max. 10 MB) — die KI liest Kaufdatum,
   Betrag, Produktname und (falls auf dem Beleg genannt) die **Garantiedauer** aus
3. Wähle das zugehörige Produkt aus oder lege es direkt neu an — bei erkannter
   Garantiedauer wird das Garantieende automatisch vorbefüllt
   (z. B. „3 Jahre Herstellergarantie" statt pauschal +2 Jahre)
4. Prüfe die Felder und klicke auf **Hochladen**

Belege kannst du jederzeit **im Browser ansehen** (Symbol „in neuem Tab öffnen")
oder herunterladen.

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

#### Produkt-Detailseite

Klicke auf den **Namen** eines Produkts, um seine Detailseite zu öffnen: Stammdaten
mit Seriennummer, Restgarantie als Fortschrittsbalken, verknüpfte Versicherung und
**alle Kaufbelege** direkt darunter (ansehen, hochladen, löschen).

#### Produkte suchen und filtern

Suche möglich nach:
- Produktname
- Kategorie
- verknüpfter Versicherung

Filter möglich nach:
- alle
- läuft bald ab
- abgelaufen
- Archiv (erscheint, sobald archivierte Produkte existieren)

#### Produkt bearbeiten oder löschen

Nutze in der Tabelle das Stift- oder Papierkorb-Symbol.

Hinweis: Beim Löschen eines Produkts werden **alle zugehörigen Rechnungen mitgelöscht** —
unabhängig von deren Aufbewahrungsfrist.

#### Produkt archivieren statt löschen

Wenn du ein Gerät **verkauft oder entsorgt** hast, ist Archivieren (auf der
Detailseite) die bessere Wahl: Das Produkt verschwindet aus den aktiven Listen,
der Garantie-Ampel und den Erinnerungen — die Kaufbelege bleiben aber bis zum
Ende ihrer Aufbewahrungsfrist erhalten. Über den Archiv-Filter findest du es
jederzeit wieder und kannst es reaktivieren.

#### Datenlücken erkennen

Produkte mit fehlendem **Kaufbeleg** (im Garantiefall dein Nachweis!),
Garantieende oder Kaufdatum zeigen ein oranges Warnsymbol. Das Dashboard fasst
zusammen, wie viele Produkte betroffen sind.

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

#### Fristen im eigenen Kalender abonnieren

Unter dem Zeitstrahl findest du die Karte **Im eigenen Kalender abonnieren**
mit einer Kalender-Adresse (ICS). Wenn du sie in deiner Kalender-App abonnierst,
erscheinen alle Vertragsabläufe, Garantieenden und jährlichen Kündigungsfristen
automatisch im Handy- oder Familienkalender und bleiben aktuell:

- **Apple Kalender (Mac):** Ablage → Neues Kalenderabonnement → Adresse einfügen
- **iPhone:** Einstellungen → Kalender → Accounts → Account hinzufügen → Andere →
  Kalenderabo hinzufügen
- **Google Kalender (Web):** Weitere Kalender → „+" → Per URL
- **Thunderbird:** Neuer Kalender → Im Netzwerk → iCalendar (ICS)

Die Adresse funktioniert nur für Geräte im Heimnetz.

### 7. Erinnerungen prüfen und Pushover testen

Öffne **Erinnerungen**.

Hier siehst du den Verlauf aller Frist-Warnungen mit Status:

- **gesendet** — die Push-Nachricht ist raus
- **ausstehend** — wird beim nächsten Lauf (täglich 8:00 Uhr) gesendet
- **fehlgeschlagen** — Versand hat nicht geklappt (wird bis 3 Tage lang erneut
  versucht); die Fehlermeldung steht dabei

Mit **Test-Push senden** prüfst du sofort, ob Pushover richtig konfiguriert ist —
so fällt ein Konfigurationsfehler auf, bevor eine echte Frist verpasst wird.

### 8. Chat-Assistent verwenden

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
- `Enter` (`Shift + Enter` für eine neue Zeile)

Der Chatverlauf bleibt beim Wechseln zwischen den Seiten erhalten. Mit
**Neuer Chat** startest du eine frische Unterhaltung.

#### Beispiel-Fragen nutzen

Beim ersten Öffnen zeigt die Ansicht Beispiel-Fragen an. Ein Klick übernimmt die Frage ins Eingabefeld.

#### Suchindex prüfen

Über **Suchindex prüfen** (oben rechts im Assistenten) kannst du kontrollieren,
ob alle hochgeladenen Dokumente für die Suche indiziert sind. Fehlende Dokumente
werden automatisch nachindiziert — das kann einige Minuten dauern. Nützlich,
wenn der Assistent ein Dokument nicht zu kennen scheint.

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

### Ich möchte Fristen auf dem Handy sehen

1. Öffne **Kalender**
2. Kopiere die Adresse unter **Im eigenen Kalender abonnieren**
3. Abonniere sie in deiner Kalender-App (siehe Anleitung im Kalender-Bereich)

Zusätzlich sendet die Anwendung automatisch Pushover-Benachrichtigungen:
- 90/30/7 Tage vor Vertragsablauf bzw. Garantieende
- 30/7 Tage vor einer Kündigungsfrist („kündbar bis") — jedes Jahr aufs Neue

## Fehlerbehebung

### Upload funktioniert nicht

Prüfe:
- ob die Datei PDF, PNG oder JPEG ist
- ob die Datei unter dem Limit liegt (Dokumente 80 MB, Rechnungen 10 MB)
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
- ob die Quellen zur Antwort angezeigt werden
- ob das hochgeladene Dokument einen Textlayer enthielt (bei gescannten PDFs wird
  automatisch Vision-OCR verwendet; bei sehr schlechter Bildqualität kann die
  Erkennung unvollständig sein)
- ob alle Dokumente indiziert sind: im Assistenten **Suchindex prüfen** ausführen

## Zusätzliche Dokumentation

Für technische Details und die Struktur des Frontends:

- `docs/FRONTEND_DOKUMENTATION.md`
- `README.md`
- `AGENTS.md`
