export const insuranceCategories = [
  'KFZ',
  'Haftpflicht',
  'Hausrat',
  'Gebäude',
  'Kranken',
  'Zahnzusatz',
  'Unfall',
  'Rechtsschutz',
  'Leben',
  'Reise',
  'Tier',
  'Geräteversicherung',
  'Sonstige',
]

export const paymentIntervals = [
  'monatlich',
  'vierteljährlich',
  'halbjährlich',
  'jährlich',
  'einmalig',
  'unbekannt',
]

export const navItems = [
  { to: '/', title: 'Dashboard', icon: 'mdi-view-dashboard', description: 'Überblick, Kosten und nächste Fristen' },
  { to: '/insurances', title: 'Versicherungen', icon: 'mdi-shield', description: 'Verträge verwalten und Empfehlungen abrufen' },
  { to: '/products', title: 'Produkte / Garantien', icon: 'mdi-package-variant', description: 'Garantien und verknüpfte Produkte pflegen' },
  { to: '/invoices', title: 'Rechnungen', icon: 'mdi-receipt-text', description: 'Kaufbelege archivieren und Aufbewahrungsfristen verfolgen' },
  { to: '/calendar', title: 'Kalender', icon: 'mdi-calendar', description: 'Laufzeiten im Zeitstrahl sehen' },
  { to: '/upload', title: 'Dokument hochladen', icon: 'mdi-cloud-upload', description: 'Police per PDF oder Foto analysieren' },
  { to: '/chat', title: 'Assistent', icon: 'mdi-robot', description: 'Fragen zu deinen Daten stellen' },
]

export const chatExampleQuestions = [
  'Wann läuft meine nächste Versicherung ab?',
  'Welche Verträge kosten mich monatlich am meisten?',
  'Welche Produkte haben bald kein Garantieende mehr?',
  'Welche Versicherungen gehören zur Kategorie Haftpflicht?',
]
