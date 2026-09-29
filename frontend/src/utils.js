import { computed, ref, watch } from 'vue'
import { useTheme } from 'vuetify'
import { intervalsPerYear } from './constants'

/**
 * Basis-Optionen, die ApexCharts an das aktive Vuetify-Theme koppeln.
 * ApexCharts kennt das Theme nicht: ohne diese Werte rendern Legende, Achsen
 * und Tooltips im Dark Mode in dunklem Grau auf dunklem Grund.
 * In der View mit den eigenen Optionen mischen — verschachtelte Schlüssel
 * (`chart`, `legend`, …) dabei explizit zusammenführen, nicht überschreiben.
 */
export function useChartTheme() {
  const theme = useTheme()
  return computed(() => {
    const dark = theme.global.current.value.dark
    const foreground = dark ? '#e0e0e0' : '#424242'
    return {
      theme: { mode: dark ? 'dark' : 'light' },
      // Ohne 'transparent' malt ApexCharts im Dark Mode einen eigenen
      // schwarzen Kasten in die Karte
      chart: { background: 'transparent', foreColor: foreground },
      legend: { labels: { colors: foreground } },
      tooltip: { theme: dark ? 'dark' : 'light' },
      grid: { borderColor: dark ? '#424242' : '#e0e0e0' },
    }
  })
}

/**
 * Ref, deren Wert in localStorage überlebt (z.B. Statusfilter je Ansicht).
 * Fällt bei Speicherfehlern still auf den Default zurück.
 */
export function persistedRef(key, defaultValue) {
  let initial = defaultValue
  try {
    const raw = localStorage.getItem(key)
    if (raw != null) initial = JSON.parse(raw)
  } catch {
    /* defekter Eintrag → Default */
  }
  const r = ref(initial)
  watch(r, (v) => {
    try {
      localStorage.setItem(key, JSON.stringify(v))
    } catch {
      /* Speicher voll o.ä. — Persistenz ist nur Komfort */
    }
  })
  return r
}

export const parseDateValue = (value) => {
  if (!value) return null
  if (value instanceof Date) return value
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split('-').map(Number)
    return new Date(year, month - 1, day)
  }
  return new Date(value)
}

// Date → 'YYYY-MM-DD' in lokaler Zeit. toISOString() rechnet in UTC um und
// verschiebt das Datum an Sommerzeit-Grenzen um einen Tag.
export const toIsoDate = (date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

export const formatCurrency = (value) =>
  value == null
    ? '–'
    : new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(value)

export const formatDate = (value) =>
  value ? new Intl.DateTimeFormat('de-DE', { dateStyle: 'medium' }).format(parseDateValue(value)) : '–'

// Für HTML-Strings in ApexCharts-Custom-Tooltips (Namen sind Nutzereingaben)
export function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

export const daysUntil = (value) => {
  if (!value) return null
  const targetDate = parseDateValue(value)
  const today = new Date()
  targetDate.setHours(0, 0, 0, 0)
  today.setHours(0, 0, 0, 0)
  // round statt ceil: an DST-Grenzen sind Tage 23/25 h lang — ceil würde dort einen Tag zu viel zählen
  return Math.round((targetDate.getTime() - today.getTime()) / 86400000)
}

export const expiryColor = (value) => {
  const days = daysUntil(value)
  if (days == null) return 'grey'
  if (days < 0) return 'grey'
  if (days < 30) return 'error'
  if (days < 90) return 'warning'
  return 'success'
}

export const daysLabel = (value, options = {}) => {
  const { capitalize = false, empty = 'kein Datum' } = options
  const days = daysUntil(value)
  if (days == null) return empty
  if (days < 0) return capitalize ? 'Abgelaufen' : 'abgelaufen'
  if (days === 0) return capitalize ? 'Heute' : 'heute'
  if (days === 1) return '1 Tag'
  return `${days} Tage`
}

export const confidenceColor = (value) =>
  ({ high: 'success', medium: 'warning', low: 'error' })[value?.toLowerCase?.()] || 'grey'

// Jahresprämie einer Versicherung (praemie_eur ist der Betrag je Zahlung), null wenn unbekannt
export const yearlyPremium = (item) =>
  item?.praemie_eur == null ? null : item.praemie_eur * (intervalsPerYear[item.zahlungsintervall] ?? 1)

/**
 * Prämien-Trend aus dem Verlauf einer Versicherung (chronologische Einträge).
 * Rückgabe: { pct, sinceYear, firstYearly, lastYearly } oder null (kein/zu wenig Verlauf).
 */
export function premiumTrend(rows) {
  if (!rows || rows.length < 2) return null
  const yearly = (r) =>
    r.praemie_eur == null ? null : r.praemie_eur * (intervalsPerYear[r.zahlungsintervall] ?? 1)
  const first = yearly(rows[0])
  const last = yearly(rows[rows.length - 1])
  if (!first || last == null) return null
  const pct = Math.round(((last - first) / first) * 100)
  if (pct === 0) return null
  return {
    pct,
    sinceYear: new Date(rows[0].changed_at).getFullYear(),
    firstYearly: first,
    lastYearly: last,
  }
}

/**
 * Datenqualitäts-Check je Vertrag: liefert Hinweise auf Lücken, durch die
 * Erinnerungen oder Auswertungen ins Leere laufen würden.
 * Bewusst nicht "kein Enddatum" allein bemängeln — bei sich jährlich
 * verlängernden Verträgen ist die Kündigungsfrist der relevante Termin.
 */
export function qualityIssues(item, hasDocuments = true) {
  const issues = []
  const hatKuendigung = Boolean(item.kuendigung_bis_tag && item.kuendigung_bis_monat)
  if (!item.end_date && !hatKuendigung) {
    issues.push('Keine Frist hinterlegt (Enddatum oder Kündigungsfrist) — es können keine Erinnerungen gesendet werden')
  }
  if (item.praemie_eur == null) {
    issues.push('Keine Prämie hinterlegt — fehlt in der Kostenübersicht')
  }
  if (!hasDocuments) {
    issues.push('Kein Dokument hinterlegt — für den Assistenten nicht auffindbar')
  }
  return issues
}

/**
 * Datenqualitäts-Check je Produkt. Wichtigster Fall: fehlender Kaufbeleg —
 * im Garantiefall ist er der Anspruchsnachweis. Archivierte Produkte werden
 * nicht bemängelt.
 */
export function productQualityIssues(product, hasInvoices = true) {
  if (product.archived) return []
  const issues = []
  if (!hasInvoices) {
    issues.push('Kein Kaufbeleg hinterlegt — im Garantiefall fehlt der Nachweis')
  }
  if (!product.warranty_end && !product.linked_insurance_id) {
    issues.push('Kein Garantieende hinterlegt — es können keine Erinnerungen gesendet werden')
  }
  if (!product.purchase_date) {
    issues.push('Kein Kaufdatum hinterlegt')
  }
  return issues
}

/**
 * Gesetzliche Gewährleistung in Deutschland. Dient als Annahme, wenn am Produkt
 * kein Garantieende gepflegt ist — sonst zählte jedes Produkt ohne Datum
 * fälschlich als "keine Garantie".
 */
export const ASSUMED_WARRANTY_YEARS = 2

/**
 * Effektives Garantieende: eigenes Datum, ersatzweise Kaufdatum + 2 Jahre
 * (Annahme), und das Ende einer verknüpften Geräteversicherung, falls es
 * später liegt. Null, wenn es keinerlei Anhaltspunkt gibt.
 *
 * Bewusst nur für Auswertungen gedacht: Erinnerungen und die Garantie-Ampel
 * laufen weiter über das tatsächlich hinterlegte Datum im Backend.
 */
export function effectiveWarrantyEnd(product, linkedInsurance = null) {
  if (!product) return null
  let end = parseDateValue(product.warranty_end)
  if (!end) {
    const purchase = parseDateValue(product.purchase_date)
    if (purchase) {
      end = new Date(
        purchase.getFullYear() + ASSUMED_WARRANTY_YEARS,
        purchase.getMonth(),
        purchase.getDate()
      )
    }
  }
  const insuranceEnd = parseDateValue(linkedInsurance?.end_date)
  if (insuranceEnd && (!end || insuranceEnd > end)) end = insuranceEnd
  return end
}

/** Steht das Produkt heute noch unter Garantie? */
export function hasActiveWarranty(product, linkedInsurance = null) {
  const end = effectiveWarrantyEnd(product, linkedInsurance)
  if (!end) return false
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return end >= today
}

/** Beruht das Garantieende nur auf der 2-Jahres-Annahme? */
export function isWarrantyAssumed(product, linkedInsurance = null) {
  return Boolean(
    product && !product.warranty_end && !linkedInsurance?.end_date && product.purchase_date
  )
}

const MAX_TAG_IM_MONAT = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

// (30, 9) → "30.09." — leere Eingaben → ''
export const formatRecurringDate = (tag, monat) =>
  tag && monat ? `${String(tag).padStart(2, '0')}.${String(monat).padStart(2, '0')}.` : ''

/**
 * Parst ein wiederkehrendes Datum ohne Jahr ("30.09.", "30.9", "1.1.").
 * Rückgabe: { tag, monat } | null (leer) | undefined (ungültig).
 */
export function parseRecurringDate(value) {
  if (value == null || String(value).trim() === '') return null
  const m = String(value).trim().match(/^(\d{1,2})\.(\d{1,2})\.?$/)
  if (!m) return undefined
  const tag = Number(m[1])
  const monat = Number(m[2])
  if (monat < 1 || monat > 12 || tag < 1 || tag > MAX_TAG_IM_MONAT[monat - 1]) return undefined
  return { tag, monat }
}

/**
 * Berechnet die nächste Kündigungsdeadline und das zugehörige Vertragsende.
 * Gibt { deadline: Date, wirksamZum: Date|null } oder null zurück.
 *
 * deadline   = nächstes Jahresvorkommen von "kündbar bis" (TT.MM.)
 * wirksamZum = nächstes Vorkommen von "endet zum" NACH der Deadline
 *              (z.B. bis 30.09. → endet 31.12. im selben Jahr;
 *               bis 30.11. → endet 01.01. im Folgejahr)
 */
// Ungültige Kombinationen (29.02. in Nicht-Schaltjahren) werden wie im Backend
// (next_recurring_date, monthrange) auf den letzten Tag des Monats geklemmt —
// sonst rollt new Date() auf den 01.03. und Anzeige und Erinnerung widersprechen sich.
const clampedYearlyDate = (year, monat, tag) => {
  const lastDay = new Date(year, monat, 0).getDate()
  return new Date(year, monat - 1, Math.min(tag, lastDay))
}

export function getCancellationInfo(item) {
  if (!item.kuendigung_bis_tag || !item.kuendigung_bis_monat) return null

  const today = new Date()
  today.setHours(0, 0, 0, 0)

  let deadline = clampedYearlyDate(today.getFullYear(), item.kuendigung_bis_monat, item.kuendigung_bis_tag)
  if (deadline < today) {
    deadline = clampedYearlyDate(today.getFullYear() + 1, item.kuendigung_bis_monat, item.kuendigung_bis_tag)
  }

  let wirksamZum = null
  if (item.kuendigung_zum_tag && item.kuendigung_zum_monat) {
    wirksamZum = clampedYearlyDate(deadline.getFullYear(), item.kuendigung_zum_monat, item.kuendigung_zum_tag)
    if (wirksamZum <= deadline) {
      wirksamZum = clampedYearlyDate(deadline.getFullYear() + 1, item.kuendigung_zum_monat, item.kuendigung_zum_tag)
    }
  }

  return { deadline, wirksamZum }
}
