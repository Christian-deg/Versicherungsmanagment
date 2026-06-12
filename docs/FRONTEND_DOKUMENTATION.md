# Frontend-Dokumentation

## Ziel

Diese Datei dokumentiert die aktuelle Frontend-Struktur des Versicherungs-Assistenten, die wichtigsten
Bedienabläufe sowie die zuletzt sichtbaren UI-Anpassungen. Sie richtet sich an Entwickler und
Projektverantwortliche, die nachvollziehen möchten, wie die Oberfläche aufgebaut ist und welche
Nutzerführung aktuell umgesetzt wurde.

## Technische Basis

- Framework: Vue 3
- UI-Bibliothek: Vuetify 3
- Build-Tool: Vite
- Diagramme: ApexCharts
- Routing: Vue Router mit History-Modus
- API-Kommunikation: Axios über `/api`

## Navigationsstruktur

Die Anwendung verwendet eine feste Hauptnavigation mit responsivem Verhalten:

- **Desktop / Tablet groß**: permanenter linker Navigation-Drawer
- **Mobil / kleine Displays**: Drawer wird über das Menü-Icon in der App-Bar geöffnet
- **Schnellaktion oben rechts**: `Schnell hochladen` führt direkt zum Upload

### Hauptbereiche

1. **Dashboard** – Überblick, Kosten und nächste Fristen
2. **Versicherungen** – Verträge verwalten, bearbeiten, exportieren, Empfehlungen abrufen
3. **Produkte / Garantien** – Produkte und Garantien verwalten
4. **Rechnungen & Kaufbelege** – Kaufbelege je Produkt hochladen und verwalten
5. **Kalender** – Zeitstrahl für Laufzeiten und Garantiezeiträume
6. **Dokument hochladen** – Datei hochladen, KI-Vorschau prüfen, Vertrag speichern
7. **Assistent** – Chat mit Quellenangaben und Konfidenz

## Wichtige Frontend-Anpassungen

Die aktuelle Oberfläche enthält bereits mehrere UX-orientierte Anpassungen:

- **Klarere Orientierung in jeder Ansicht**
  - Jede Hauptseite beginnt mit Titel und kurzer Einordnung.
  - Primäre Aktionen sind direkt im Header der jeweiligen Seite sichtbar.

- **Geführter Einstieg**
  - App-Bar mit Upload-Schnellzugriff
  - Navigation-Drawer mit erklärenden Beschreibungen pro Bereich
  - Empfehlungsbox im Drawer mit vorgeschlagenem Ablauf

- **Verbesserte Leerstati**
  - Dashboard, Versicherungen, Produkte und Kalender zeigen explizite Empty States
  - Nutzer erhalten direkte Folgeaktionen statt leerer Tabellen oder leerer Flächen

- **Filter- und Suchführung**
  - Versicherungen und Produkte bieten Suchfelder mit klarer Suchlogik
  - Status-Chips ermöglichen schnelles Filtern nach kritischen oder abgelaufenen Einträgen

- **Direkte Arbeitsabläufe ohne Umwege**
  - Upload führt nach dem Speichern direkt zur Vertragsliste
  - Dashboard verweist direkt zu Upload, Chat und Kalender
  - Export-Aktionen sind in der Vertragsübersicht sofort verfügbar

- **Bessere Chat-Bedienung**
  - Beispiel-Fragen für den Einstieg
  - Senden per Button sowie per `Strg/⌘ + Enter`
  - Quellen- und Konfidenzanzeige direkt in der Antwort

## Detailbeschreibung der Ansichten

### 1. Dashboard

Zweck:
- schneller Überblick über Verträge, Kosten und Fristen

Inhalte:
- Hero-Bereich mit Statuszusammenfassung
- Kennzahlenkarten für:
  - aktive Versicherungen
  - monatliche Gesamtkosten
  - nächster Ablauf
  - aktive Garantien
- Donut-Chart für Kosten nach Kategorie
- Garantie-Statusliste
- Liste der nächsten Abläufe

Besonderheiten:
- Wenn keine Daten vorhanden sind, wird ein motivierender Einstiegstext angezeigt.
- Bei kommenden Fristen wird visuell zwischen unkritisch, bald fällig und kritisch unterschieden.

### 2. Versicherungen

Zweck:
- zentrale Pflege aller Verträge

Inhalte:
- Suchfeld für Name, Kategorie, Versicherer und Vertragsnummer
- Statusfilter:
  - alle
  - läuft bald ab
  - abgelaufen
- Datentabelle mit Bearbeiten-, Empfehlung- und Löschen-Aktion
- Export nach PDF und Excel
- Dialog für Neuanlage und Bearbeitung

Pflichtfelder im Dialog:
- Name
- Kategorie
- Versicherer
- Vertragsnummer

Besonderheiten:
- Nach einem erfolgreichen Dokument-Upload wird ein gespeicherter Vertrag mit Erfolgsmeldung angezeigt.
- Für jeden Vertrag kann eine Empfehlung über den Backend-Service angefordert werden.

### 3. Produkte & Garantien

Zweck:
- Verwaltung von Produkten mit Garantiezeiträumen

Inhalte:
- Suche nach Produkt, Kategorie oder verknüpfter Versicherung
- Statusfilter für bald endende und abgelaufene Garantien
- Datentabelle mit Bearbeiten- und Löschen-Aktion
- Dialog zur Pflege von:
  - Produktname
  - freier Kategorie
  - Kaufdatum
  - Garantieende
  - optional verknüpfter Versicherung
  - Notizen

Besonderheiten:
- Produkte können optional mit einer Versicherung verknüpft werden.
- Ein Garantieende verbessert Fristenübersicht und spätere Benachrichtigungen.

### 5. Rechnungen & Kaufbelege

Zweck:
- Kaufbelege zu Produkten hochladen und Aufbewahrungsfristen verwalten

Inhalte:
- Upload-Dialog mit Produktauswahl, Datei, Kaufdatum, Betrag und Notizen
- Filterchips: alle / demnächst fällig / abgelaufen
- Listendarstellung mit Aufbewahrungsfrist und Löschen-Aktion

Besonderheiten:
- Aufbewahrungsfrist wird automatisch berechnet: `max(Kaufdatum + 730 Tage, Garantieende)`
- Löschen nur möglich nach Ablauf der Frist; vorher wird das Fristende angezeigt
- Beim Löschen eines Produkts werden alle zugehörigen Rechnungen mitgelöscht

### 5. Kalender / Zeitstrahl

Zweck:
- gemeinsame visuelle Darstellung von Versicherungs- und Garantiezeiträumen

Inhalte:
- ApexCharts-Range-Bar-Diagramm
- Versicherungen und Produkte in einer gemeinsamen Zeitachse

Besonderheiten:
- Es werden nur Einträge mit vollständigen Datumswerten angezeigt.
- Der Tooltip bereitet Namen und Datumswerte sicher auf.
- Ohne verwertbare Daten wird ein leerer Zustand mit Erklärung angezeigt.

### 6. Dokument hochladen

Zweck:
- bestehende Police als PDF oder Bild einlesen und per KI vorbefüllen

Unterstützte Dateitypen:
- PDF
- PNG
- JPEG

Maximale Dateigröße:
- 10 MB

Ablauf:
1. Datei auswählen
2. `Hochladen & analysieren` starten
3. KI-Vorschlag in der Extraktionsvorschau prüfen
4. erkannte Felder bei Bedarf korrigieren
5. Vertrag bestätigen und speichern

Bearbeitbare Felder in der Vorschau:
- Versicherer
- Kategorie
- frei wählbarer Name
- Vertragsnummer
- Start
- Ende
- Prämie
- Zahlungsintervall

Pflichtlogik vor dem Speichern:
- Kategorie muss vorhanden sein
- Versicherer muss vorhanden sein
- Vertragsnummer muss vorhanden sein
- ein Vertragsname muss vorhanden sein

Besonderheiten:
- Die Konfidenz wird farblich hervorgehoben.
- Hinweise aus der Extraktion werden in einem Info-Hinweis angezeigt.
- Nutzer können den Vorgang verwerfen und neu starten.

### 7. Assistent / Chat

Zweck:
- Fragen in natürlicher Sprache zu vorhandenen Versicherungs- und Produktdaten beantworten

Inhalte:
- leere Startansicht mit Beispiel-Fragen
- Chatverlauf mit Trennung zwischen Nutzer und Assistent
- Quellen-Chips pro Antwort
- Konfidenz-Chip pro Antwort
- Eingabefeld mit Sende-Button

Bedienung:
- Senden über Button
- Senden über `Strg + Enter` oder `⌘ + Enter`

Besonderheiten:
- Der Assistent kann Fragen zu Stammdaten (Prämien, Laufzeiten) **und** zu konkreten
  Vertragsbedingungen (Selbstbehalt, Deckungsumfang, Ausschlüsse) beantworten, sofern
  beim Upload ein Textlayer vorhanden war oder Vision-OCR erfolgreich war.
- Bei Fehlern wird die Fehlermeldung als Assistentenantwort in den Chat aufgenommen.
- Der Nachrichtenbereich scrollt nach jeder Nachricht automatisch nach unten.

## API-Nutzung im Frontend

Verwendete Bereiche:

- `insurancesApi`
  - Listen
  - Einzelabruf
  - Anlegen
  - Aktualisieren
  - Löschen
  - Finanzzusammenfassung

- `productsApi`
  - Listen
  - Anlegen
  - Aktualisieren
  - Löschen
  - Garantie-Zusammenfassung

- `invoicesApi`
  - Rechnung hochladen (multipart/form-data)
  - Listen (optional nach Produkt gefiltert)
  - Löschen (nur nach Ablauf der Aufbewahrungsfrist)

- `documentsApi`
  - Dokument hochladen
  - bestätigte Extraktion speichern
  - Empfehlung abrufen

- `chatApi`
  - Frage an Chat-Endpunkt senden

## Responsive Verhalten

- Die Hauptnavigation passt sich an die Bildschirmgröße an.
- Aktionsbereiche in den Ansichten umbrechen auf kleineren Displays.
- Eingabe- und Aktionsbereiche im Chat wechseln zwischen Spalten- und Zeilenlayout.
- Tabellen, Chips und Karten bleiben auf Mobilgeräten bedienbar.

## Aktueller Dokumentationsstand

Die bisherige Projektdokumentation in `README.md` und `AGENTS.md` beschreibt bereits das Projekt,
die Architektur und die wichtigsten Features. Diese Datei ergänzt speziell die **konkreten
Frontend-Abläufe, Seiteninhalte und Bedienmuster**, damit die sichtbaren UI-Anpassungen separat und
nachvollziehbar dokumentiert sind.
