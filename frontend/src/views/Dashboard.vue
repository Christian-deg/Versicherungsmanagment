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
            <v-sheet color="white" rounded="lg" class="pa-4 text-primary">
              <div class="text-overline">In den nächsten 90 Tagen</div>
              <div class="text-h4">{{ upcomingExpiries.length }}</div>
              <div class="text-body-2">
                {{ upcomingExpiries.length ? 'Fristen rechtzeitig prüfen' : 'Keine kritischen Abläufe erkannt' }}
              </div>
            </v-sheet>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <v-row>
      <v-col cols="12" sm="6" md="3">
        <v-card color="primary" theme="dark">
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
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card color="warning" theme="dark">
          <v-skeleton-loader v-if="initialLoading" type="list-item" color="warning" theme="dark" />
          <v-card-text v-else>
            <div class="text-overline">Nächster Ablauf</div>
            <div class="text-h6">{{ nextExpiryLabel }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card color="success" theme="dark">
          <v-skeleton-loader v-if="initialLoading" type="list-item" color="success" theme="dark" />
          <v-card-text v-else>
            <div class="text-overline">Garantien aktiv</div>
            <div class="text-h3">{{ (warranty?.green || 0) + (warranty?.yellow || 0) }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mt-2">
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Kosten nach Kategorie (p.a.)</v-card-title>
          <v-card-text v-if="categoryChartSeries.length">
            <apexchart type="donut" :options="categoryChartOptions" :series="categoryChartSeries" height="320" />
          </v-card-text>
          <v-card-text v-else class="text-medium-emphasis">Noch keine Daten</v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
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
    </v-row>

    <v-card class="mt-4">
      <v-card-title class="d-flex align-center">
        Nächste Abläufe
        <v-spacer />
        <v-btn variant="text" color="primary" to="/calendar">Im Kalender öffnen</v-btn>
      </v-card-title>
      <v-card-text>
        <v-list v-if="upcomingItems.length" lines="two">
          <v-list-item v-for="item in upcomingItems" :key="item.id">
            <template #prepend>
              <v-avatar color="primary" variant="tonal">
                <v-icon icon="mdi-shield" />
              </v-avatar>
            </template>
            <v-list-item-title>{{ item.name }}</v-list-item-title>
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

    <v-snackbar v-model="error.show" color="error">{{ error.text }}</v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { insurancesApi, productsApi } from '../api'
import { daysLabel, expiryColor, formatCurrency, formatDate, daysUntil } from '../utils'

const insurances = ref([])
const financial = ref(null)
const warranty = ref(null)
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
const upcomingExpiries = computed(() => sortedExpiries.value.filter((item) => {
  const days = daysUntil(item.end_date)
  return days != null && days >= 0 && days <= 90
}))
const nextExpiryLabel = computed(() =>
  upcomingItems.value[0] ? formatDate(upcomingItems.value[0].end_date) : '–'
)
const summaryText = computed(() => {
  if (!insurances.value.length) {
    return 'Starte am einfachsten mit dem Upload einer bestehenden Police, damit die Daten automatisch vorbefüllt werden.'
  }
  return `${formatCurrency(financial.value?.total_month_eur)} pro Monat · ${formatCurrency(financial.value?.total_year_eur)} pro Jahr · ${upcomingExpiries.value.length} Fristen in den nächsten 90 Tagen`
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
    insurances.value = await insurancesApi.list()
    financial.value = await insurancesApi.financial()
    warranty.value = await productsApi.warrantyStatus()
  } catch (e) {
    error.value = { show: true, text: 'Dashboard konnte nicht geladen werden: ' + (e.response?.data?.detail || e.message) }
  } finally {
    initialLoading.value = false
  }
})
</script>
