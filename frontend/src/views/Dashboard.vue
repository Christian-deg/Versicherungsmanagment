<template>
  <div>
    <div class="d-flex flex-column flex-md-row align-start align-md-center mb-4 ga-3">
      <div>
        <h1 class="text-h4">Dashboard</h1>
        <p class="text-medium-emphasis mt-1">
          Behalte Kosten, Fristen und Garantien mit wenigen Blicken im Auge.
        </p>
      </div>
      <v-spacer />
      <div class="d-flex flex-wrap ga-2">
        <v-btn color="primary" prepend-icon="mdi-cloud-upload" to="/upload">Dokument hochladen</v-btn>
        <v-btn variant="outlined" prepend-icon="mdi-robot" to="/chat">Assistent fragen</v-btn>
        <v-tooltip text="Komplett-Backup herunterladen (Datenbank + alle Dokumente und Belege)" location="bottom">
          <template #activator="{ props }">
            <v-btn
              v-bind="props"
              variant="outlined"
              prepend-icon="mdi-database-export"
              href="/api/exports/backup.zip"
            >
              Backup
            </v-btn>
          </template>
        </v-tooltip>
      </div>
    </div>

    <v-card class="mb-4" color="primary" theme="dark" rounded="xl">
      <v-skeleton-loader v-if="initialLoading" type="list-item-two-line" color="primary" theme="dark" />
      <v-card-text v-else class="py-6">
        <v-row align="center">
          <v-col cols="12" md="8">
            <div class="text-overline mb-2">Schnellüberblick</div>
            <div class="text-h5 mb-2">
              {{ insurances.length ? `Du verwaltest aktuell ${insurances.length} Versicherungen.` : 'Lege jetzt deine ersten Verträge an.' }}
            </div>
            <div class="text-body-1 text-primary-lighten-5">
              {{ summaryText }}
            </div>
          </v-col>
          <v-col cols="12" md="4">
            <v-sheet
              color="white"
              rounded="lg"
              class="pa-4 text-primary"
              :style="upcomingDeadlineCount ? 'cursor: pointer' : ''"
              @click="upcomingDeadlineCount && (deadlineDetailsOpen = !deadlineDetailsOpen)"
            >
              <div class="d-flex align-center justify-space-between">
                <div class="text-overline">Fristen in den nächsten 90 Tagen</div>
                <v-icon v-if="upcomingDeadlineCount" size="small">
                  {{ deadlineDetailsOpen ? 'mdi-chevron-up' : 'mdi-chevron-down' }}
                </v-icon>
              </div>
              <div class="text-h4">{{ upcomingDeadlineCount }}</div>
              <div class="text-body-2">
                {{ upcomingDeadlineCount
                  ? (deadlineDetailsOpen ? 'Antippen zum Einklappen' : 'Antippen für Details')
                  : 'Keine Fristen in den nächsten 90 Tagen' }}
              </div>
              <v-expand-transition>
                <div v-show="deadlineDetailsOpen">
                  <v-divider class="my-2" />
                  <div
                    v-for="d in upcomingDeadlines"
                    :key="d.key"
                    class="d-flex align-center justify-space-between py-1 ga-2"
                  >
                    <div class="flex-grow-1" style="min-width: 0">
                      <div class="text-truncate">
                        <router-link
                          :to="`/insurances/${d.id}`"
                          class="text-primary font-weight-medium text-decoration-none"
                          @click.stop
                        >
                          {{ d.name }}
                        </router-link>
                      </div>
                      <div class="text-caption">{{ d.label }} {{ formatDate(d.date) }}</div>
                    </div>
                    <v-chip :color="expiryColor(d.date)" size="x-small" variant="flat" class="flex-shrink-0">
                      {{ daysLabel(d.date) }}
                    </v-chip>
                  </div>
                </div>
              </v-expand-transition>
            </v-sheet>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <v-alert
      v-if="!initialLoading && (incompleteInsurances.length || incompleteProducts.length)"
      type="warning"
      variant="tonal"
      class="mb-4"
    >
      {{ incompleteSummary }} — Erinnerungen, Auswertungen oder Garantienachweise können dort
      ins Leere laufen. Details stehen als Warnsymbol in den Listen.
      <template #append>
        <v-btn
          variant="text"
          color="warning"
          :to="incompleteInsurances.length ? '/insurances' : '/products'"
        >
          Prüfen
        </v-btn>
      </template>
    </v-alert>

    <v-row>
      <v-col cols="12" sm="6" md="3">
        <v-card color="primary" theme="dark" to="/insurances" link>
          <v-skeleton-loader v-if="initialLoading" type="list-item" color="primary" theme="dark" />
          <v-card-text v-else>
            <div class="text-overline">Aktive Versicherungen</div>
            <div class="text-h3">{{ insurances.length }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card color="secondary" theme="dark">
          <v-skeleton-loader v-if="initialLoading" type="list-item" color="secondary" theme="dark" />
          <v-card-text v-else>
            <div class="text-overline">Kosten</div>
            <div class="text-h4">{{ formatEur(financial?.total_month_eur) }} <span class="text-body-2">/ Monat</span></div>
            <div class="text-h6 mt-1">{{ formatEur(financial?.total_year_eur) }} <span class="text-body-2">/ Jahr</span></div>
            <div v-if="personBreakdown" class="text-caption mt-1">{{ personBreakdown }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card
          color="warning"
          theme="dark"
          :to="upcomingItems[0] ? `/insurances/${upcomingItems[0].id}` : '/calendar'"
          link
        >
          <v-skeleton-loader v-if="initialLoading" type="list-item" color="warning" theme="dark" />
          <v-card-text v-else>
            <div class="text-overline">Nächster Ablauf</div>
            <div class="text-h6">{{ nextExpiryLabel }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card color="success" theme="dark" to="/products" link>
          <v-skeleton-loader v-if="initialLoading" type="list-item" color="success" theme="dark" />
          <v-card-text v-else>
            <div class="text-overline">Garantien aktiv</div>
            <div class="text-h3">{{ (warranty?.green || 0) + (warranty?.yellow || 0) }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mt-2">
      <v-col cols="12" md="4">
        <v-card height="100%">
          <v-card-title>Kosten nach Kategorie (p.a.)</v-card-title>
          <v-card-text v-if="categoryChartSeries.length">
            <apexchart type="donut" :options="categoryChartOptions" :series="categoryChartSeries" height="320" />
          </v-card-text>
          <v-card-text v-else class="text-medium-emphasis">Noch keine Daten</v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="4">
        <v-card height="100%">
          <v-card-title>Garantie-Status</v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item v-for="(label, key) in warrantyLabels" :key="key">
                <template #prepend>
                  <v-icon :color="warrantyColors[key]">mdi-circle</v-icon>
                </template>
                <v-list-item-title>{{ label }}</v-list-item-title>
                <template #append>
                  <span class="text-h6">{{ warranty?.[key] || 0 }}</span>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="4">
        <v-card height="100%">
          <v-card-title>
            <v-icon icon="mdi-treasure-chest" class="mr-2" />Erfasster Warenwert
          </v-card-title>
          <v-card-text>
            <div class="text-h3 mb-1">{{ formatEur(inventoryValue) }}</div>
            <div class="text-body-2 text-medium-emphasis mb-3">
              aus {{ inventoryReceipts }} Beleg{{ inventoryReceipts === 1 ? '' : 'en' }}
              zu deinen aktiven Produkten
            </div>
            <v-alert type="info" variant="tonal" density="compact">
              Vergleiche den Wert mit der Deckungssumme deiner Hausratversicherung —
              im Schadensfall ist die Belegliste dein Nachweis.
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-card v-if="costTimeline.length >= 2" class="mt-4">
      <v-card-title>
        <v-icon icon="mdi-chart-line" class="mr-2" />Kostenentwicklung (Jahresprämie gesamt)
      </v-card-title>
      <v-card-text>
        <apexchart type="line" :options="costChartOptions" :series="costChartSeries" height="240" />
      </v-card-text>
    </v-card>

    <v-row class="mt-1">
      <v-col cols="12" md="7">
        <v-card height="100%">
          <v-card-title class="d-flex align-center">
            Nächste Abläufe
            <v-spacer />
            <v-btn variant="text" color="primary" to="/calendar">Im Kalender öffnen</v-btn>
          </v-card-title>
          <v-card-text>
            <v-list v-if="upcomingItems.length" lines="two">
              <v-list-item v-for="item in upcomingItems" :key="item.id" :to="`/insurances/${item.id}`" link>
                <template #prepend>
                  <v-avatar color="primary" variant="tonal">
                    <v-icon :icon="categoryIcon(item.kategorie)" />
                  </v-avatar>
                </template>
                <v-list-item-title class="text-primary">{{ item.name }}</v-list-item-title>
                <v-list-item-subtitle>
                  {{ item.versicherer }} · endet am {{ formatDate(item.end_date) }}
                </v-list-item-subtitle>
                <template #append>
                  <v-chip :color="expiryColor(item.end_date)" size="small">
                    {{ daysLabel(item.end_date) }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
            <v-empty-state
              v-else
              headline="Noch keine kommenden Abläufe"
              text="Sobald Verträge mit Enddatum vorhanden sind, erscheinen sie hier."
              icon="mdi-calendar-check"
            />
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="5">
        <v-card height="100%">
          <v-card-title class="d-flex align-center">
            Nächste Kündigungsfristen
            <v-spacer />
            <v-btn variant="text" color="primary" to="/insurances">Zu den Verträgen</v-btn>
          </v-card-title>
          <v-card-text>
            <v-list v-if="cancellationItems.length" lines="two">
              <v-list-item v-for="item in cancellationItems" :key="item.id" :to="`/insurances/${item.id}`" link>
                <template #prepend>
                  <v-avatar color="warning" variant="tonal">
                    <v-icon icon="mdi-calendar-remove" />
                  </v-avatar>
                </template>
                <v-list-item-title class="text-primary">{{ item.name }}</v-list-item-title>
                <v-list-item-subtitle>
                  kündbar bis {{ formatDate(item.deadline) }}<template v-if="item.wirksamZum">
                    · endet dann {{ formatDate(item.wirksamZum) }}</template>
                </v-list-item-subtitle>
                <template #append>
                  <v-chip :color="expiryColor(item.deadline)" size="small">
                    {{ daysLabel(item.deadline) }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
            <v-empty-state
              v-else
              headline="Keine Kündigungsfristen hinterlegt"
              text="Trage bei deinen Verträgen „kündbar bis&quot; ein, um Fristen hier zu sehen."
              icon="mdi-calendar-remove-outline"
            />
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-snackbar v-model="error.show" color="error">{{ error.text }}</v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { documentsApi, insurancesApi, invoicesApi, productsApi } from '../api'
import { categoryIcon } from '../constants'
import {
  daysLabel,
  expiryColor,
  formatCurrency,
  formatDate,
  daysUntil,
  getCancellationInfo,
  parseDateValue,
  productQualityIssues,
  qualityIssues,
  yearlyPremium,
} from '../utils'

const insurances = ref([])
const financial = ref(null)
const warranty = ref(null)
const documents = ref([])
const products = ref([])
const invoices = ref([])
const premiumHistory = ref([])
const error = ref({ show: false, text: '' })

const warrantyLabels = {
  green: 'Lange Restlaufzeit (>90 Tage)',
  yellow: '30–90 Tage',
  red: 'Kritisch (<30 Tage)',
  expired: 'Abgelaufen',
  no_warranty: 'Ohne Garantie-Datum',
}
const warrantyColors = {
  green: 'success',
  yellow: 'warning',
  red: 'error',
  expired: 'grey',
  no_warranty: 'grey-lighten-1',
}

const sortedExpiries = computed(() =>
  [...insurances.value]
    .filter((item) => {
      if (!item.end_date) return false
      const days = daysUntil(item.end_date)
      return days != null && days >= 0
    })
    .sort((a, b) => new Date(a.end_date) - new Date(b.end_date))
)

const upcomingItems = computed(() => sortedExpiries.value.slice(0, 5))

// Verträge mit Datenlücken (fehlende Frist, Prämie oder Dokument)
const incompleteInsurances = computed(() => {
  const withDocs = new Set(documents.value.filter((d) => d.insurance_id != null).map((d) => d.insurance_id))
  return insurances.value.filter((i) => qualityIssues(i, withDocs.has(i.id)).length > 0)
})

// Produkte mit Datenlücken (fehlender Beleg, Garantieende oder Kaufdatum)
const incompleteProducts = computed(() => {
  const withInvoices = new Set(invoices.value.map((i) => i.product_id))
  return products.value.filter((p) => productQualityIssues(p, withInvoices.has(p.id)).length > 0)
})

const incompleteSummary = computed(() => {
  const parts = []
  if (incompleteInsurances.value.length) {
    const n = incompleteInsurances.value.length
    parts.push(n === 1 ? '1 Vertrag' : `${n} Verträge`)
  }
  if (incompleteProducts.value.length) {
    const n = incompleteProducts.value.length
    parts.push(n === 1 ? '1 Produkt' : `${n} Produkte`)
  }
  const subject = parts.join(' und ')
  const singular = incompleteInsurances.value.length + incompleteProducts.value.length === 1
  return `${subject} ${singular ? 'hat' : 'haben'} unvollständige Daten`
})

// Kostenaufteilung nach Person (nur anzeigen, wenn Personen zugeordnet sind)
const personBreakdown = computed(() => {
  const byPerson = financial.value?.by_person || {}
  const entries = Object.entries(byPerson).filter(([k]) => k !== 'Ohne Zuordnung')
  if (!entries.length) return ''
  return entries.map(([person, value]) => `${person}: ${formatCurrency(value)} p.a.`).join(' · ')
})

// Kostenentwicklung: Gesamt-Jahresprämie zu jedem Zeitpunkt des Prämienverlaufs.
// Je Versicherung gilt der jeweils letzte bekannte Stand (Stufenverlauf).
const costTimeline = computed(() => {
  const sorted = [...premiumHistory.value].sort(
    (a, b) => new Date(a.changed_at) - new Date(b.changed_at)
  )
  const currentByInsurance = new Map()
  const points = []
  for (const row of sorted) {
    currentByInsurance.set(row.insurance_id, yearlyPremium(row) ?? 0)
    const total = [...currentByInsurance.values()].reduce((a, b) => a + b, 0)
    const x = new Date(row.changed_at).getTime()
    if (points.length && points[points.length - 1].x === x) {
      points[points.length - 1].y = Math.round(total * 100) / 100
    } else {
      points.push({ x, y: Math.round(total * 100) / 100 })
    }
  }
  return points
})

const costChartSeries = computed(() => [{ name: 'Jahresprämie gesamt', data: costTimeline.value }])
const costChartOptions = {
  chart: { toolbar: { show: false }, zoom: { enabled: false } },
  stroke: { curve: 'stepline', width: 3 },
  xaxis: { type: 'datetime', labels: { datetimeUTC: false } },
  yaxis: { labels: { formatter: (v) => formatCurrency(v) } },
  tooltip: { x: { format: 'dd.MM.yyyy' }, y: { formatter: (v) => formatCurrency(v) } },
  dataLabels: { enabled: false },
  markers: { size: 4 },
}

// Erfasster Warenwert: Summe der Belegbeträge aktiver (nicht archivierter) Produkte
const inventoryValue = computed(() => {
  const active = new Set(products.value.filter((p) => !p.archived).map((p) => p.id))
  return invoices.value
    .filter((i) => active.has(i.product_id) && i.amount_eur != null)
    .reduce((sum, i) => sum + i.amount_eur, 0)
})
const inventoryReceipts = computed(() => {
  const active = new Set(products.value.filter((p) => !p.archived).map((p) => p.id))
  return invoices.value.filter((i) => active.has(i.product_id) && i.amount_eur != null).length
})

// Kündigungs-Deadlines aller Verträge mit hinterlegtem "kündbar bis"
const allCancellations = computed(() =>
  insurances.value
    .map((item) => {
      const info = getCancellationInfo(item)
      return info ? { id: item.id, name: item.name, ...info } : null
    })
    .filter(Boolean)
    .sort((a, b) => a.deadline - b.deadline)
)

const cancellationItems = computed(() => allCancellations.value.slice(0, 5))

// Kündigungsfristen innerhalb der nächsten 90 Tage
const upcomingCancellations = computed(() =>
  allCancellations.value.filter((c) => {
    const days = daysUntil(c.deadline)
    return days != null && days >= 0 && days <= 90
  })
)

// Der 90-Tage-Zähler umfasst Vertragsabläufe UND Kündigungsfristen — bei sich
// jährlich verlängernden Verträgen (ohne Enddatum) ist die Kündigungsfrist
// die eigentlich kritische Frist
const upcomingDeadlineCount = computed(
  () => upcomingExpiries.value.length + upcomingCancellations.value.length
)
const upcomingExpiries = computed(() => sortedExpiries.value.filter((item) => {
  const days = daysUntil(item.end_date)
  return days != null && days >= 0 && days <= 90
}))

// Ausklappbare Detail-Liste zur 90-Tage-Kachel: alle Fristen einzeln, mit Link zum Vertrag
const deadlineDetailsOpen = ref(false)
const upcomingDeadlines = computed(() =>
  [
    ...upcomingExpiries.value.map((item) => ({
      key: `end-${item.id}`,
      id: item.id,
      name: item.name,
      date: item.end_date,
      label: 'endet am',
    })),
    ...upcomingCancellations.value.map((item) => ({
      key: `cancel-${item.id}`,
      id: item.id,
      name: item.name,
      date: item.deadline,
      label: 'kündbar bis',
    })),
  ].sort((a, b) => parseDateValue(a.date) - parseDateValue(b.date))
)
const nextExpiryLabel = computed(() =>
  upcomingItems.value[0] ? formatDate(upcomingItems.value[0].end_date) : '–'
)
const summaryText = computed(() => {
  if (!insurances.value.length) {
    return 'Starte am einfachsten mit dem Upload einer bestehenden Police, damit die Daten automatisch vorbefüllt werden.'
  }
  return `${formatCurrency(financial.value?.total_month_eur)} pro Monat · ${formatCurrency(financial.value?.total_year_eur)} pro Jahr · ${upcomingDeadlineCount.value} Frist${upcomingDeadlineCount.value === 1 ? '' : 'en'} in den nächsten 90 Tagen`
})

const categoryChartSeries = computed(() => Object.values(financial.value?.by_category || {}))
const categoryChartOptions = computed(() => ({
  labels: Object.keys(financial.value?.by_category || {}),
  legend: { position: 'bottom' },
  // Absolute Euro-Werte auf den Segmenten statt Prozente
  dataLabels: {
    enabled: true,
    formatter: (val, opts) => formatCurrency(opts.w.globals.series[opts.seriesIndex]),
  },
  tooltip: {
    y: { formatter: (val) => formatCurrency(val) },
  },
  plotOptions: {
    pie: {
      donut: {
        labels: {
          show: true,
          value: { formatter: (val) => formatCurrency(Number(val)) },
          total: {
            show: true,
            label: 'Gesamt p.a.',
            formatter: (w) => formatCurrency(w.globals.seriesTotals.reduce((a, b) => a + b, 0)),
          },
        },
      },
    },
  },
}))

const formatEur = formatCurrency
const initialLoading = ref(true)
onMounted(async () => {
  try {
    // Parallel laden — die Abfragen sind unabhängig
    ;[
      insurances.value,
      financial.value,
      warranty.value,
      documents.value,
      products.value,
      invoices.value,
      premiumHistory.value,
    ] = await Promise.all([
      insurancesApi.list(),
      insurancesApi.financial(),
      productsApi.warrantyStatus(),
      documentsApi.list(),
      productsApi.list(),
      invoicesApi.list(),
      insurancesApi.premiumHistory(),
    ])
  } catch (e) {
    error.value = { show: true, text: 'Dashboard konnte nicht geladen werden: ' + (e.response?.data?.detail || e.message) }
  } finally {
    initialLoading.value = false
  }
})
</script>
