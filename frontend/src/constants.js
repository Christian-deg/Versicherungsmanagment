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

// Zahlungen pro Jahr je Intervall (Spiegel von INTERVALS_PER_YEAR im Backend)
export const intervalsPerYear = {
  monatlich: 12,
  vierteljährlich: 4,
  halbjährlich: 2,
  jährlich: 1,
  einmalig: 0,
  unbekannt: 1,
}

// Icon je Versicherungskategorie — für schnellere visuelle Erfassung in Listen
export const categoryIcons = {
  KFZ: 'mdi-car',
  Haftpflicht: 'mdi-shield-account',
  Hausrat: 'mdi-sofa',
  Gebäude: 'mdi-home-city',
  Kranken: 'mdi-heart-pulse',
  Zahnzusatz: 'mdi-tooth',
  Unfall: 'mdi-bandage',
  Rechtsschutz: 'mdi-scale-balance',
  Leben: 'mdi-heart',
  Reise: 'mdi-airplane',
  Tier: 'mdi-paw',
  Geräteversicherung: 'mdi-devices',
  Sonstige: 'mdi-shield',
}

export const categoryIcon = (kategorie) => categoryIcons[kategorie] || 'mdi-shield'

// Vorschläge für Produkt-Kategorien (Dropdown). Bereits verwendete Kategorien
// kommen im ProductCategoryField automatisch dazu; eigene bleiben möglich.
export const productCategories = [
  'Audio',
  'Computer',
  'Fahrrad',
  'Filmen',
  'Fotografieren',
  'Garten',
  'Haushaltsgerät',
  'Konsole & Gaming',
  'Kühlgerät',
  'Licht',
  'Möbel',
  'Netzwerk',
  'Rucksack',
  'Smartphone & Tablet',
  'TV',
  'Uhr & Schmuck',
  'Unterhaltungselektronik',
  'Werkzeug',
  'Sonstiges',
]

// Produkt-Kategorien sind Freitext — Icon per Stichwort-Heuristik
const productIconRules = [
  [/handy|smartphone|phone|tablet/i, 'mdi-cellphone'],
  [/laptop|notebook|computer|pc|monitor/i, 'mdi-laptop'],
  [/tv|fernseher|beamer/i, 'mdi-television'],
  [/kamera|camera|foto|drohne/i, 'mdi-camera'],
  [/audio|kopfhörer|lautsprecher|mikro/i, 'mdi-headphones'],
  [/licht|lampe|leucht/i, 'mdi-lightbulb'],
  [/netzwerk|router|repeater|wlan/i, 'mdi-router-wireless'],
  [/elektro|elektronik|gerät/i, 'mdi-devices'],
  [/wasch|trockner|kühl|spül|herd|ofen|haushalt|küche/i, 'mdi-washing-machine'],
  [/möbel|sofa|schrank|bett/i, 'mdi-sofa'],
  [/werkzeug|maschine/i, 'mdi-tools'],
  [/fahrrad|bike|roller/i, 'mdi-bike'],
  [/auto|kfz/i, 'mdi-car'],
  [/garten/i, 'mdi-flower'],
  [/uhr|schmuck/i, 'mdi-watch'],
  [/spiel|konsole|gaming/i, 'mdi-gamepad-variant'],
]

export function productIcon(kategorie) {
  const k = String(kategorie || '')
  for (const [pattern, icon] of productIconRules) {
    if (pattern.test(k)) return icon
  }
  return 'mdi-package-variant'
}

export const navItems = [
  { to: '/', title: 'Dashboard', icon: 'mdi-view-dashboard', description: 'Überblick, Kosten und nächste Fristen' },
  { to: '/insurances', title: 'Versicherungen', icon: 'mdi-shield', description: 'Verträge verwalten und Empfehlungen abrufen' },
  { to: '/products', title: 'Produkte / Garantien', icon: 'mdi-package-variant', description: 'Garantien und verknüpfte Produkte pflegen' },
  { to: '/invoices', title: 'Rechnungen', icon: 'mdi-receipt-text', description: 'Kaufbelege archivieren und Aufbewahrungsfristen verfolgen' },
  { to: '/calendar', title: 'Kalender', icon: 'mdi-calendar', description: 'Laufzeiten im Zeitstrahl sehen' },
  { to: '/notifications', title: 'Erinnerungen', icon: 'mdi-bell-ring', description: 'Gesendete Warnungen prüfen, Test-Push senden' },
  { to: '/upload', title: 'Dokument hochladen', icon: 'mdi-cloud-upload', description: 'Police per PDF oder Foto analysieren' },
  { to: '/chat', title: 'Assistent', icon: 'mdi-robot', description: 'Fragen zu deinen Daten stellen' },
]

// Achsen-Beschriftung für ApexCharts-Datetime-Achsen: deutsche, numerische
// Formate statt englischer Monatsnamen — und bei engem Zeitbereich (alle
// Einträge am selben Tag) das Datum statt Uhrzeiten wie "20:00"
export const datetimeAxisLabels = {
  datetimeUTC: false,
  datetimeFormatter: {
    year: 'yyyy',
    month: 'MM.yyyy',
    day: 'dd.MM.yyyy',
    hour: 'dd.MM.yyyy',
    minute: 'dd.MM.yyyy',
  },
}

export const chatExampleQuestions = [
  'Wann läuft meine nächste Versicherung ab?',
  'Welche Verträge kosten mich monatlich am meisten?',
  'Welche Produkte haben bald kein Garantieende mehr?',
  'Welche Versicherungen gehören zur Kategorie Haftpflicht?',
]
