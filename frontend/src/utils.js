export const parseDateValue = (value) => {
  if (!value) return null
  if (value instanceof Date) return value
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split('-').map(Number)
    return new Date(year, month - 1, day)
  }
  return new Date(value)
}

export const formatCurrency = (value) =>
  value == null
    ? '–'
    : new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(value)

export const formatDate = (value) =>
  value ? new Intl.DateTimeFormat('de-DE', { dateStyle: 'medium' }).format(parseDateValue(value)) : '–'

export const daysUntil = (value) => {
  if (!value) return null
  const targetDate = parseDateValue(value)
  const today = new Date()
  targetDate.setHours(0, 0, 0, 0)
  today.setHours(0, 0, 0, 0)
  return Math.ceil((targetDate.getTime() - today.getTime()) / 86400000)
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
export function getCancellationInfo(item) {
  if (!item.kuendigung_bis_tag || !item.kuendigung_bis_monat) return null

  const today = new Date()
  today.setHours(0, 0, 0, 0)

  let deadline = new Date(today.getFullYear(), item.kuendigung_bis_monat - 1, item.kuendigung_bis_tag)
  if (deadline < today) {
    deadline = new Date(today.getFullYear() + 1, item.kuendigung_bis_monat - 1, item.kuendigung_bis_tag)
  }

  let wirksamZum = null
  if (item.kuendigung_zum_tag && item.kuendigung_zum_monat) {
    wirksamZum = new Date(deadline.getFullYear(), item.kuendigung_zum_monat - 1, item.kuendigung_zum_tag)
    if (wirksamZum <= deadline) {
      wirksamZum.setFullYear(wirksamZum.getFullYear() + 1)
    }
  }

  return { deadline, wirksamZum }
}
