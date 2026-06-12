<template>
  <div>
    <div class="d-flex flex-column flex-md-row align-start align-md-center mb-4 ga-3">
      <div>
        <h1 class="text-h4">Kalender / Zeitstrahl</h1>
        <p class="text-medium-emphasis mt-1">
          Vergleiche Laufzeiten von Versicherungen und Garantien in einer gemeinsamen Zeitleiste.
        </p>
      </div>
    </div>

    <v-alert type="info" variant="tonal" class="mb-4">
      Tipp: Nutze den Zeitstrahl, um Überschneidungen und bald endende Fristen schneller zu erkennen.
    </v-alert>

    <v-card>
      <v-card-text>
        <div class="d-flex flex-wrap ga-3 mb-4">
          <v-chip prepend-icon="mdi-circle" color="#1976d2" variant="tonal" size="small">Versicherung</v-chip>
          <v-chip prepend-icon="mdi-circle" color="#26a69a" variant="tonal" size="small">Produkt / Garantie</v-chip>
        </div>
        <apexchart v-if="series[0]?.data?.length" type="rangeBar" :options="options" :series="series" height="500" />
        <v-empty-state
          v-else
          headline="Keine Termine vorhanden"
          text="Sobald Versicherungen oder Produkte mit Datumsangaben vorliegen, erscheinen sie hier im Zeitstrahl."
          icon="mdi-calendar-blank-outline"
        />
      </v-card-text>
    </v-card>

    <v-snackbar v-model="error.show" color="error">{{ error.text }}</v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { insurancesApi, productsApi } from '../api'
import { formatDate, parseDateValue } from '../utils'

const insurances = ref([])
const products = ref([])
const error = ref({ show: false, text: '' })

const series = computed(() => {
  const insData = insurances.value
    .filter((i) => i.start_date && i.end_date)
    .map((i) => ({ x: `🛡 ${i.name}`, y: [parseDateValue(i.start_date).getTime(), parseDateValue(i.end_date).getTime()], fillColor: '#1976d2' }))
  const prodData = products.value
    .filter((p) => p.purchase_date && p.warranty_end)
    .map((p) => ({ x: `📦 ${p.name}`, y: [parseDateValue(p.purchase_date).getTime(), parseDateValue(p.warranty_end).getTime()], fillColor: '#26a69a' }))
  return [{ name: 'Laufzeit', data: [...insData, ...prodData] }]
})

const options = {
  chart: { toolbar: { show: true } },
  plotOptions: { bar: { horizontal: true, distributed: false, barHeight: '60%' } },
  xaxis: { type: 'datetime' },
  dataLabels: { enabled: false },
  legend: { show: false },
  tooltip: {
    custom({ seriesIndex, dataPointIndex, w }) {
      const d = w.globals.initialSeries[seriesIndex].data[dataPointIndex]
      const start = escapeHtml(formatDate(d.y[0]))
      const end = escapeHtml(formatDate(d.y[1]))
      return `<div class='pa-2'><strong>${escapeHtml(d.x)}</strong><br>${start} → ${end}</div>`
    },
  },
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

onMounted(async () => {
  try {
    insurances.value = await insurancesApi.list()
    products.value = await productsApi.list()
  } catch (e) {
    error.value = { show: true, text: 'Kalender konnte nicht geladen werden: ' + (e.response?.data?.detail || e.message) }
  }
})
</script>
