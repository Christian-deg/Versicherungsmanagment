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
- API-Kommunikation: Axios über `/api` (Standard-Timeout 60 s; KI-Analysen und
  Uploads 300 s, Chat 120 s)
- PWA: Web-App-Manifest + Icons — die App lässt sich auf dem Handy zum
  Startbildschirm hinzufügen und startet dann im Vollbild (kein Service Worker,
  kein Offline-Modus)

## Design / Dark Mode

- Umschalter (Mond/Sonne) oben rechts in der App-Bar
- Beim ersten Besuch folgt das Design der System-Einstellung
  (`prefers-color-scheme`), danach wird die Wahl in `localStorage` gespeichert
- Farbpaletten für hell und dunkel sind in `main.js` definiert; Komponenten
  verwenden theme-taugliche Farben (`tonal`-Varianten statt fester Hellgrau-Töne)

## Navigationsstruktur

Die Anwendung verwendet eine feste Hauptnavigation mit responsivem Verhalten:

- **Desktop / Tablet groß**: permanenter linker Navigation-Drawer
- **Mobil / kleine Displays**: Drawer wird über das Menü-Icon in der App-Bar geöffnet
- **Schnellaktion oben rechts**: `Schnell hochladen` führt direkt zum Upload
- **Globale Suche** (App-Bar, ab md-Breite): findet Verträge und Produkte;
  Treffer führen direkt zur Vertrags-Detailseite bzw. zur vorgefilterten
  Produktliste (`/products?search=…`)
- `router-view` ist mit `:key="route.path"` versehen, damit beim Wechsel
  zwischen Detailseiten (z. B. `/insurances/3` → `/insurances/5`) neu geladen wird

### Hauptbereiche

1. **Dashboard** – Überblick, Kosten und nächste Fristen
2. **Versicherungen** – Verträge verwalten, bearbeiten, exportieren, Empfehlungen abrufen
3. **Produkte / Garantien** – Produkte und Garantien verwalten
4. **Rechnungen & Kaufbelege** – Kaufbelege je Produkt hochladen und verwalten
5. **Kalender** – Zeitstrahl für Laufzeiten und Garantiezeiträume
6. **Erinnerungen** – Verlauf der Frist-Warnungen und Pushover-Test
7. **Dokument hochladen** – Datei hochladen, KI-Vorschau prüfen, Vertrag speichern
8. **Assistent** – Chat mit Quellenangaben und Konfidenz

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
- Karte „Erfasster Warenwert": Summe der Belegbeträge aktiver Produkte —
  als Abgleich mit der Deckungssumme der Hausratversicherung
- Kostenentwicklungs-Chart (Stufenlinie der Gesamt-Jahresprämie aus dem
  Prämienverlauf; erscheint ab zwei Datenpunkten)
- Kosten-Kachel zeigt zusätzlich die Aufteilung nach Person, sobald Verträge
  ein „gehört zu"-Label haben
- Backup-Button im Kopfbereich (`/api/exports/backup.zip`)
- Liste der nächsten Abläufe
- Liste der nächsten Kündigungsfristen („kündbar bis", mit Datum des dann
  wirksamen Vertragsendes)

Besonderheiten:
- Wenn keine Daten vorhanden sind, wird ein motivierender Einstiegstext angezeigt.
- Bei kommenden Fristen wird visuell zwischen unkritisch, bald fällig und kritisch unterschieden.
- Datenqualitäts-Hinweis: Haben Verträge oder Produkte Lücken (fehlende Frist,
  Prämie, Dokument bzw. Kaufbeleg, Garantieende, Kaufdatum), erscheint ein
  Warnhinweis mit Link zur jeweiligen Liste.

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
- Der Vertragsname ist verlinkt und führt zur **Vertrags-Detailseite**
  (`/insurances/{id}`).
- Kategorie-Chips zeigen ein passendes Icon je Kategorie (Auto, Haus, Zahn …).
- Die Prämien-Spalte (und die mobile Karte) zeigt zusätzlich die Jahresprämie und
  den prozentualen Anteil an den Gesamtkosten, z. B. „311,00 € p.a. · 28 % der
  Gesamtkosten"; bei Prämienänderungen erscheint ein Trend-Chip
  („+18 % seit 2024", rot bei Erhöhung, grün bei Senkung).
- Der Statusfilter wird in `localStorage` gemerkt (ebenso bei Produkten und
  Rechnungen), genauso der Personen-Filter.
- Personen-Zuordnung: Verträge können ein „gehört zu"-Label tragen (Combobox
  mit Vorschlägen aus Bestandsdaten); vorhandene Labels erscheinen als
  Filter-Chips und als Chip am Vertrag.
- Löschen mit Undo: Der Eintrag verschwindet sofort, der eigentliche
  API-Aufruf läuft erst nach 5 Sekunden — die Snackbar bietet solange
  „Rückgängig" an (ebenso bei Produkten). Beim Verlassen der Seite wird eine
  ausstehende Löschung sofort ausgeführt.
- Das Bearbeiten-Formular ist als wiederverwendbare Komponente umgesetzt
  (`components/InsuranceFormDialog.vue`) und wird von Liste und Detailseite
  gemeinsam genutzt.
- Nach einem erfolgreichen Dokument-Upload wird ein gespeicherter Vertrag mit Erfolgsmeldung angezeigt.
- Für jeden Vertrag kann eine Empfehlung über den Backend-Service angefordert werden.
- Über das Büroklammer-Symbol öffnet sich der Dokumente-Dialog: vorhandene
  Unterlagen **im Browser ansehen** (öffnet in neuem Tab), neue Dokumente
  anhängen (werden volltextindiziert) und einzelne Dokumente löschen.
- Datenqualitäts-Check: Verträge mit Lücken (keine Frist, keine Prämie, kein
  Dokument) zeigen ein Warnsymbol neben dem Namen (Tooltip mit Details);
  in der mobilen Kartenansicht stehen die Hinweise als Textzeilen.

### 2b. Vertrags-Detailseite (`/insurances/{id}`)

Zweck:
- alles zu einem Vertrag auf einer Seite statt in verteilten Dialogen

Inhalte:
- Kopfbereich mit Zurück-Navigation, „Frage zum Vertrag" (öffnet den
  Assistenten mit vorbefülltem Bezug), Bearbeiten (gemeinsamer
  Formular-Dialog) und Löschen (mit Bestätigung)
- Datenqualitäts-Hinweise als Alert (falls Lücken vorhanden)
- **Stammdaten**: Kategorie (mit Icon), Prämie inkl. Jahreswert, Laufzeit,
  Restlaufzeit, nächste Kündigungsfrist, Notizen
- **Prämienverlauf**: Zeitleiste aller erfassten Prämienstände mit Trend-Chip
- **Dokumente**: ansehen (Browser-Tab), neue anhängen, löschen
- **KI-Empfehlung**: gespeicherte Einschätzung anzeigen und neu bewerten

### 3. Produkte & Garantien

Zweck:
- Verwaltung von Produkten mit Garantiezeiträumen

Inhalte:
- Suche nach Produkt, Kategorie oder verknüpfter Versicherung
- Statusfilter für bald endende und abgelaufene Garantien sowie ein
  **Archiv**-Filter (erscheint, sobald archivierte Produkte existieren)
- Datentabelle mit Bearbeiten- und Löschen-Aktion; Produktnamen verlinken auf
  die Produkt-Detailseite; Kategorie-Chips mit Stichwort-basiertem Icon
- Formular-Dialog (gemeinsame Komponente `components/ProductFormDialog.vue`,
  auch von der Detailseite genutzt) zur Pflege von:
  - Produktname
  - freier Kategorie
  - Seriennummer (optional, für Garantiefälle)
  - Kaufdatum
  - Garantieende
  - optional verknüpfter Versicherung
  - Notizen

Besonderheiten:
- Produkte können optional mit einer Versicherung verknüpft werden.
- Ein Garantieende verbessert Fristenübersicht und spätere Benachrichtigungen.
- Datenqualitäts-Check: fehlender Kaufbeleg, fehlendes Garantieende oder
  fehlendes Kaufdatum werden als Warnsymbol (Tabelle) bzw. Hinweiszeilen
  (mobile Karten) angezeigt; archivierte Produkte werden nicht bemängelt.

### 3b. Produkt-Detailseite (`/products/{id}`)

Zweck:
- alles zu einem Produkt auf einer Seite — inklusive der Kaufbelege

Inhalte:
- Kopfbereich mit Zurück-Navigation, „Frage zum Produkt" (Assistent mit
  vorbefülltem Bezug), Bearbeiten, **Archivieren/Reaktivieren** und Löschen
  (der Lösch-Dialog bietet „Lieber archivieren" als sanfte Alternative)
- Stammdaten & Garantie: Kategorie (Icon), Seriennummer, Kaufdatum,
  Garantieende und **Restgarantie als Fortschrittsbalken**
- Verknüpfte Versicherung als Link zur Vertrags-Detailseite
- Kaufbelege: ansehen (Browser-Tab), herunterladen, löschen (mit
  Fristprüfung + Bestätigungs-Checkbox), direkter Upload sowie Link in den
  KI-Analyse-Ablauf der Rechnungs-Seite

### 5. Rechnungen & Kaufbelege

Zweck:
- Kaufbelege zu Produkten hochladen und Aufbewahrungsfristen verwalten

Inhalte:
- Upload-Dialog mit Produktauswahl, Datei, Kaufdatum, Betrag und Notizen;
  erkennt der Beleg eine Garantiedauer (`garantie_monate`), wird das
  Garantieende eines neu angelegten Produkts automatisch vorbefüllt
- Filterchips: alle / demnächst fällig / abgelaufen
- Listendarstellung mit Aufbewahrungsfrist, Ansehen- (Browser-Tab),
  Download- und Löschen-Aktion

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
- Karte „Im eigenen Kalender abonnieren": zeigt die ICS-Feed-Adresse
  (`/api/exports/calendar.ics`) mit Kopier- und Download-Button — zum
  Abonnieren in Apple/Google Kalender oder Thunderbird

Besonderheiten:
- Es werden nur Einträge mit vollständigen Datumswerten angezeigt.
- Der Tooltip bereitet Namen und Datumswerte sicher auf.
- Ohne verwertbare Daten wird ein leerer Zustand mit Erklärung angezeigt.
- Der Kopier-Button hat einen Fallback für HTTP im LAN (die Clipboard-API
  steht nur in Secure Contexts zur Verfügung).

### 6. Erinnerungen

Zweck:
- nachvollziehen, welche Frist-Warnungen erzeugt und gesendet wurden

Inhalte:
- Liste aller Notifications (neueste zuerst) mit Status-Chip
  (gesendet / ausstehend / fehlgeschlagen), Fälligkeitsdatum, Warnstufe und
  bei Fehlern der Fehlermeldung
- Symbol je Typ: Vertrag (Schild), Garantie (Paket), Kündigungsfrist (Kalender)
- Button **Test-Push senden** zum Prüfen der Pushover-Konfiguration

### 7. Dokument hochladen

Zweck:
- bestehende Police als PDF oder Bild einlesen und per KI vorbefüllen

Unterstützte Dateitypen:
- PDF
- PNG
- JPEG

Maximale Dateigröße:
- 80 MB für Versicherungsdokumente
- 10 MB für Rechnungen (nach Weiterleitung in den Rechnungs-Ablauf)

Ablauf:
1. Datei auswählen — auf Mobilgeräten alternativ **„Mit Kamera aufnehmen"**
   (verstecktes Input mit `capture="environment"`, öffnet direkt die Rückkamera;
   gleiches Muster im Rechnungs-Upload)
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
- Während der Analyse wird darauf hingewiesen, dass gescannte, mehrseitige
  Dokumente einige Minuten dauern können.
- **Duplikat-Erkennung**: Existiert bereits ein Vertrag mit derselben
  Vertragsnummer (normalisiert, d. h. ohne Leer-/Trennzeichen), erscheint in der
  Vorschau ein Warnhinweis mit zwei Optionen — „Anhängen + Laufzeit/Prämie
  aktualisieren" (Dokument an den Bestandsvertrag, Felder aus der Vorschau
  übernehmen) oder „Nur Dokument anhängen". Alternativ kann normal ein neuer
  Vertrag angelegt werden.

### 8. Assistent / Chat

Zweck:
- Fragen in natürlicher Sprache zu vorhandenen Versicherungs- und Produktdaten beantworten

Inhalte:
- leere Startansicht mit Beispiel-Fragen
- Chatverlauf mit Trennung zwischen Nutzer und Assistent
- Quellen-Chips pro Antwort
- Konfidenz-Chip pro Antwort
- Eingabefeld mit Sende-Button
- Kopfzeilen-Aktionen: „Suchindex prüfen" (Embedding-Wartung) und „Neuer Chat"

Bedienung:
- Senden über Button oder `Enter` (`Shift + Enter` für neue Zeile)
- „Neuer Chat" leert den Verlauf

Besonderheiten:
- Der Chatverlauf wird pro Browser-Tab gespeichert (sessionStorage) und
  übersteht damit Seitenwechsel innerhalb der App.
- Während der Agent arbeitet, zeigt ein rotierender Status an, was passiert
  („Durchsuche deine Dokumente…"). Echtes Token-Streaming ist bewusst nicht
  umgesetzt: Der Output-Sicherheitsfilter prüft die vollständige Antwort,
  bevor sie den Server verlässt — Streaming würde ihn umgehen.
- „Suchindex prüfen" ruft `POST /api/documents/maintenance/reindex` auf und
  meldet per Snackbar, ob Dokumente nachindiziert werden.
- Der Assistent kann Fragen zu Stammdaten (Prämien, Laufzeiten) **und** zu konkreten
  Vertragsbedingungen (Selbstbehalt, Deckungsumfang, Ausschlüsse) beantworten, sofern
  beim Upload ein Textlayer vorhanden war oder Vision-OCR erfolgreich war.
- Bei Fehlern wird die Fehlermeldung als Assistentenantwort in den Chat aufgenommen
  (Fehler werden nicht als Kontext an das Backend zurückgesendet).
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
  - Prämienverlauf (`premiumHistory`)

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
  - Dokumenttyp erkennen (classify)
  - Dokument hochladen und analysieren
  - weitere Dokumente ohne Analyse hochladen / an Verträge anhängen
  - analysiertes Dokument bestehendem Vertrag zuordnen (`assign`, Duplikat-Erkennung)
  - bestätigte Extraktion speichern
  - Dokumente auflisten, ansehen (`/documents/{id}/file`) und löschen
  - Empfehlung abrufen und neu erzeugen
  - Suchindex-Wartung (`reindex`)

- `notificationsApi`
  - Erinnerungs-Verlauf laden
  - Test-Push senden

- `chatApi`
  - Frage an Chat-Endpunkt senden (inkl. bisherigem Verlauf)

- Exporte (direkte Links, kein Axios): PDF/Excel-Downloads und der
  ICS-Kalender-Feed `/api/exports/calendar.ics`

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
