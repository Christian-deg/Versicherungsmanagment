<template>
  <div>
    <div class="d-flex flex-column flex-md-row align-start align-md-center mb-4 ga-3">
      <div>
        <h1 class="text-h4">Produkte & Garantien</h1>
        <p class="text-medium-emphasis mt-1">
          Verfolge Garantieenden übersichtlich und verknüpfe Produkte bei Bedarf mit einer Versicherung.
        </p>
      </div>
      <v-spacer />
      <div class="d-flex flex-wrap ga-2">
        <v-btn color="primary" prepend-icon="mdi-plus" @click="openNew">Neu</v-btn>
        <v-btn variant="outlined" prepend-icon="mdi-file-excel" href="/api/exports/products.xlsx" target="_blank">Excel</v-btn>
      </div>
    </div>

    <!-- Warenwert nach Kategorie: eingeklappt nur eine Zeile, damit die Liste im Fokus bleibt -->
    <v-card v-if="!initialLoading && hasInventory" class="mb-4">
      <v-card-item style="cursor: pointer" @click="breakdownOpen = !breakdownOpen">
        <template #prepend>
          <v-icon icon="mdi-treasure-chest" />
        </template>
        <v-card-title class="text-subtitle-1">Warenwert nach Kategorie</v-card-title>
        <v-card-subtitle>
          {{ formatCurrency(breakdownTotal) }} ·
          {{ scopedStats.length }} Kategorie{{ scopedStats.length === 1 ? '' : 'n' }}
        </v-card-subtitle>
        <template #append>
          <v-icon>{{ breakdownOpen ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
        </template>
      </v-card-item>

      <!-- v-if statt v-show: ApexCharts misst beim Mounten die Container-Breite —
           in einem per display:none versteckten Block käme ein leerer Chart heraus -->
      <v-expand-transition>
        <div v-if="breakdownOpen">
          <v-divider />
          <v-card-text>
            <v-btn-toggle
              v-model="breakdownScope"
              mandatory
              variant="outlined"
              divided
              density="comfortable"
              class="mb-3"
            >
              <v-btn value="all" size="small">Alle</v-btn>
              <v-btn value="warranty" size="small">Mit Garantie</v-btn>
              <v-btn value="nowarranty" size="small">Ohne Garantie</v-btn>
            </v-btn-toggle>

            <v-row>
              <v-col cols="12" md="5">
                <apexchart
                  v-if="donutSeries.length"
                  type="donut"
                  :options="donutOptions"
                  :series="donutSeries"
                  height="300"
                />
                <div v-else class="text-medium-emphasis">Keine Belegbeträge in dieser Auswahl</div>
              </v-col>
              <v-col cols="12" md="7">
                <v-list density="compact" class="py-0 bg-transparent">
                  <v-list-item
                    v-for="stat in scopedStats"
                    :key="stat.kategorie"
                    :active="categoryFilter === stat.kategorie"
                    rounded="lg"
                    @click="toggleCategory(stat.kategorie)"
                  >
                    <template #prepend>
                      <v-icon :icon="productIcon(stat.kategorie)" class="mr-3" />
                    </template>
                    <v-list-item-title class="d-flex align-center ga-2">
                      <span class="text-truncate">{{ stat.kategorie }}</span>
                      <v-spacer />
                      <span class="font-weight-medium flex-shrink-0">
                        {{ stat.value > 0 ? formatCurrency(stat.value) : 'kein Beleg' }}
                      </span>
                    </v-list-item-title>
                    <v-list-item-subtitle>
                      {{ stat.count }} Produkt{{ stat.count === 1 ? '' : 'e' }}
                      <!-- Die Aufteilung ist nur in der Gesamtsicht eine Information;
                           in den gefilterten Ansichten wäre sie tautologisch -->
                      <template v-if="breakdownScope === 'all'">
                        <template v-if="stat.warrantyCount === stat.count">· mit Garantie</template>
                        <template v-else-if="!stat.warrantyCount">· ohne Garantie</template>
                        <template v-else>
                          · davon {{ formatCurrency(stat.warrantyValue) }}
                          mit Garantie ({{ stat.warrantyCount }})
                        </template>
                      </template>
                    </v-list-item-subtitle>
                    <v-progress-linear
                      :model-value="sharePercent(stat)"
                      color="primary"
                      height="4"
                      rounded
                      class="mt-1"
                    />
                  </v-list-item>
                </v-list>
              </v-col>
            </v-row>

            <div v-if="breakdownWithoutReceipt" class="text-caption text-medium-emphasis mt-2">
              <v-icon icon="mdi-information-outline" size="x-small" />
              {{ breakdownWithoutReceipt }} von {{ breakdownProductCount }} Produkten
              {{ breakdownWithoutReceipt === 1 ? 'hat' : 'haben' }} keinen Beleg mit Betrag —
              {{ breakdownWithoutReceipt === 1 ? 'sein' : 'ihr' }} Wert fehlt in der Summe.
            </div>
            <div v-if="breakdownAssumed" class="text-caption text-medium-emphasis mt-1">
              <v-icon icon="mdi-information-outline" size="x-small" />
              Bei {{ breakdownAssumed }} Produkt{{ breakdownAssumed === 1 ? '' : 'en' }} ohne
              hinterlegtes Garantieende sind 2 Jahre ab Kauf angenommen.
            </div>
            <div class="text-caption text-medium-emphasis mt-1">
              <v-icon icon="mdi-archive-outline" size="x-small" />
              Archivierte Produkte (verkauft oder defekt) sind nicht enthalten.
            </div>
          </v-card-text>
        </div>
      </v-expand-transition>
    </v-card>

    <v-row class="mb-1">
      <v-col cols="12" md="6">
        <v-text-field
          v-model="search"
          prepend-inner-icon="mdi-magnify"
          label="Nach Produkt, Kategorie oder verknüpfter Versicherung suchen"
          variant="outlined"
          density="comfortable"
          hide-details
        />
      </v-col>
      <v-col cols="12" md="6" class="d-flex flex-wrap align-center ga-2">
        <v-chip :color="statusFilter === 'all' ? 'primary' : undefined" @click="statusFilter = 'all'">Alle {{ activeItems.length }}</v-chip>
        <v-chip :color="statusFilter === 'warning' ? 'warning' : undefined" @click="statusFilter = 'warning'">
          Läuft bald ab ({{ expiringSoonCount }})
        </v-chip>
        <v-chip :color="statusFilter === 'expired' ? 'error' : undefined" @click="statusFilter = 'expired'">
          Abgelaufen ({{ expiredCount }})
        </v-chip>
        <v-chip
          v-if="archivedCount"
          :color="statusFilter === 'archived' ? 'secondary' : undefined"
          prepend-icon="mdi-archive"
          @click="statusFilter = 'archived'"
        >
          Archiv ({{ archivedCount }})
        </v-chip>
        <!-- Aktiver Kategorie-Filter bleibt sichtbar, auch wenn die Auswertung zugeklappt ist -->
        <v-chip
          v-if="categoryFilter"
          color="primary"
          variant="flat"
          closable
          :prepend-icon="productIcon(categoryFilter)"
          @click:close="categoryFilter = null"
        >
          Kategorie: {{ categoryFilter }}
        </v-chip>
      </v-col>
    </v-row>

    <v-skeleton-loader v-if="initialLoading" :type="smAndDown ? 'card' : 'table'" />

    <!-- Mobil: Karten -->
    <template v-else-if="smAndDown">
      <v-empty-state
        v-if="!filteredItems.length"
        :headline="emptyHeadline"
        :text="emptyText"
        :icon="archivedOnlyHint ? 'mdi-archive' : 'mdi-package-variant-closed'"
      >
        <template #actions>
          <v-btn
            v-if="archivedOnlyHint"
            color="secondary"
            prepend-icon="mdi-archive"
            @click="statusFilter = 'archived'"
          >
            Archiv anzeigen
          </v-btn>
          <v-btn v-else color="primary" prepend-icon="mdi-plus" @click="openNew">Produkt anlegen</v-btn>
        </template>
      </v-empty-state>
      <v-card v-for="item in filteredItems" :key="item.id" class="mb-3">
        <v-card-item>
          <v-card-title class="text-subtitle-1 text-wrap">
            <router-link :to="`/products/${item.id}`" class="text-decoration-none text-primary">
              {{ item.name }}
            </router-link>
            <v-chip v-if="item.archived" size="x-small" color="grey" class="ml-1">archiviert</v-chip>
          </v-card-title>
          <v-card-subtitle>
            <v-icon :icon="productIcon(item.kategorie)" size="small" class="mr-1" />{{ item.kategorie }}
          </v-card-subtitle>
        </v-card-item>
        <v-card-text class="pt-0">
          <v-chip size="small" :color="endColor(item.warranty_end)" class="mb-2">
            {{ item.warranty_end ? `Garantie: ${formatDate(item.warranty_end)} · ${daysLabel(item.warranty_end)}` : 'Kein Garantie-Datum' }}
          </v-chip>
          <div class="text-body-2">
            Gekauft: {{ item.purchase_date ? formatDate(item.purchase_date) : '–' }}
          </div>
          <div v-if="item.linked_insurance_id" class="text-body-2 text-medium-emphasis">
            Versicherung: {{ insuranceName(item.linked_insurance_id) }}
          </div>
          <div v-for="issue in issuesFor(item)" :key="issue" class="text-caption text-warning mt-1">
            <v-icon size="x-small" icon="mdi-alert-circle-outline" /> {{ issue }}
          </div>
        </v-card-text>
        <v-card-actions class="pt-0">
          <v-btn size="small" variant="text" prepend-icon="mdi-receipt-text" @click="goInvoices(item)">
            Rechnungen
          </v-btn>
          <v-spacer />
          <v-btn icon="mdi-pencil" size="small" variant="text" @click="openEdit(item)" />
          <v-btn icon="mdi-delete" size="small" variant="text" color="error" @click="confirmDelete(item)" />
        </v-card-actions>
      </v-card>
    </template>

    <!-- Desktop: Tabelle -->
    <v-data-table v-else :headers="headers" :items="filteredItems" :items-per-page="20">
      <template #item.name="{ item }">
        <router-link :to="`/products/${item.id}`" class="text-decoration-none text-primary font-weight-medium">
          {{ item.name }}
        </router-link>
        <v-chip v-if="item.archived" size="x-small" color="grey" class="ml-1">archiviert</v-chip>
        <v-tooltip v-if="issuesFor(item).length" location="top">
          <template #activator="{ props }">
            <v-icon v-bind="props" icon="mdi-alert-circle-outline" color="warning" size="small" class="ml-1" />
          </template>
          <div v-for="issue in issuesFor(item)" :key="issue">• {{ issue }}</div>
        </v-tooltip>
      </template>
      <template #item.kategorie="{ item }">
        <v-chip size="small" color="primary" variant="tonal" :prepend-icon="productIcon(item.kategorie)">
          {{ item.kategorie }}
        </v-chip>
      </template>
      <template #item.warranty_end="{ item }">
        <v-chip size="small" :color="endColor(item.warranty_end)">
          {{ item.warranty_end ? `${formatDate(item.warranty_end)} · ${daysLabel(item.warranty_end)}` : '–' }}
        </v-chip>
      </template>
      <template #item.linked_insurance_id="{ item }">
        <span v-if="item.linked_insurance_id">
          {{ insuranceName(item.linked_insurance_id) }}
        </span>
        <span v-else class="text-medium-emphasis">–</span>
      </template>
      <template #item.actions="{ item }">
        <v-tooltip text="Rechnungen anzeigen" location="top">
          <template #activator="{ props }">
            <v-btn v-bind="props" icon="mdi-receipt-text" size="small" variant="text" @click="goInvoices(item)" />
          </template>
        </v-tooltip>
        <v-tooltip text="Bearbeiten" location="top">
          <template #activator="{ props }">
            <v-btn v-bind="props" icon="mdi-pencil" size="small" variant="text" @click="openEdit(item)" />
          </template>
        </v-tooltip>
        <v-tooltip text="Löschen" location="top">
          <template #activator="{ props }">
            <v-btn v-bind="props" icon="mdi-delete" size="small" variant="text" color="error" @click="confirmDelete(item)" />
          </template>
        </v-tooltip>
      </template>
      <template #no-data>
        <v-empty-state
          :headline="emptyHeadline"
          :text="emptyText"
          :icon="archivedOnlyHint ? 'mdi-archive' : 'mdi-package-variant-closed'"
        >
          <template #actions>
            <v-btn
              v-if="archivedOnlyHint"
              color="secondary"
              prepend-icon="mdi-archive"
              @click="statusFilter = 'archived'"
            >
              Archiv anzeigen
            </v-btn>
            <v-btn v-else color="primary" prepend-icon="mdi-plus" @click="openNew">Produkt anlegen</v-btn>
          </template>
        </v-empty-state>
      </template>
    </v-data-table>

    <ProductFormDialog v-model="dialog" :product="formTarget" @saved="onSaved" />

    <!-- Bestätigungs-Dialog für Löschen -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title>Produkt löschen</v-card-title>
        <v-card-text>
          Möchtest du das Produkt <strong>„{{ deleteTarget?.name }}"</strong> wirklich löschen?
          <v-alert type="warning" variant="tonal" density="compact" class="mt-3">
            Alle zugehörigen Rechnungen werden ebenfalls gelöscht — auch wenn ihre
            Aufbewahrungsfrist noch läuft. Diese Aktion kann nicht rückgängig gemacht werden.
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="deleteDialog = false">Abbrechen</v-btn>
          <v-btn color="error" @click="onDelete">Löschen</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snack.show" :color="snack.color" :timeout="snack.undo ? 5000 : 4000">
      {{ snack.text }}
      <template v-if="snack.undo" #actions>
        <v-btn variant="text" @click="undoDelete">Rückgängig</v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'
import { productsApi, insurancesApi, invoicesApi } from '../api'
import ProductFormDialog from '../components/ProductFormDialog.vue'
import { productIcon } from '../constants'
import {
  daysLabel,
  expiryColor,
  formatCurrency,
  formatDate,
  daysUntil,
  hasActiveWarranty,
  isWarrantyAssumed,
  persistedRef,
  productQualityIssues,
  useChartTheme,
} from '../utils'

const route = useRoute()
const router = useRouter()
const { smAndDown } = useDisplay()
const items = ref([])
const insurances = ref([])
const invoices = ref([])
const dialog = ref(false)
const formTarget = ref(null)
const snack = ref({ show: false, color: 'success', text: '' })
// ?search=... aus der globalen Suche übernehmen (auch wenn die Seite schon offen ist)
const search = ref(typeof route.query.search === 'string' ? route.query.search : '')
watch(
  () => route.query.search,
  (v) => {
    if (typeof v === 'string') search.value = v
  }
)
// Filterwahl überlebt Seitenwechsel und Neustarts
const statusFilter = persistedRef('versicherung-filter-products', 'all')
// Kategorie-Filter (null = alle) — gesetzt per Klick in der Warenwert-Auswertung
const categoryFilter = persistedRef('versicherung-filter-products-category', null)
// Auswertung startet eingeklappt, damit die Produktliste im Fokus bleibt
const breakdownOpen = persistedRef('versicherung-warenwert-open', false)
// Aufteilung des Warenwerts: alle, nur mit Garantie, nur ohne Garantie
const BREAKDOWN_SCOPES = ['all', 'warranty', 'nowarranty']
const breakdownScope = persistedRef('versicherung-warenwert-scope', 'all')
// Ältere gespeicherte Werte ('active') würden den Umschalter leer lassen
if (!BREAKDOWN_SCOPES.includes(breakdownScope.value)) breakdownScope.value = 'all'
const initialLoading = ref(true)
const deleteDialog = ref(false)
const deleteTarget = ref(null)

const headers = [
  { title: 'Name', key: 'name' },
  { title: 'Kategorie', key: 'kategorie' },
  { title: 'Kaufdatum', key: 'purchase_date' },
  { title: 'Garantieende', key: 'warranty_end' },
  { title: 'Versicherung', key: 'linked_insurance_id' },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]

function insuranceName(id) {
  const ins = insurances.value.find((i) => i.id === id)
  return ins ? `${ins.name} (${ins.versicherer})` : `ID ${id}`
}

const endColor = expiryColor
// Aktive Produkte (Standard-Ansichten); Archivierte nur über den Archiv-Filter
const activeItems = computed(() => items.value.filter((i) => !i.archived))
const archivedCount = computed(() => items.value.length - activeItems.value.length)

// Produktkategorien sind Freitext — leere Angaben landen in einem eigenen Topf,
// damit sie im Warenwert nicht unsichtbar verschwinden
const categoryKey = (item) => (item.kategorie || '').trim() || 'Ohne Kategorie'

// Wert je Produkt = Summe seiner Belegbeträge. Belege ohne Betrag zählen nicht mit;
// betroffene Produkte werden unter der Auswertung ausgewiesen.
const valueByProduct = computed(() => {
  const map = new Map()
  for (const inv of invoices.value) {
    if (inv.amount_eur == null) continue
    map.set(inv.product_id, (map.get(inv.product_id) || 0) + inv.amount_eur)
  }
  return map
})

const insuranceById = computed(() => new Map(insurances.value.map((i) => [i.id, i])))
const linkedInsurance = (product) =>
  product.linked_insurance_id ? insuranceById.value.get(product.linked_insurance_id) ?? null : null

// Garantiestatus je Produkt — fehlt ein Garantieende, gelten 2 Jahre ab Kauf
const underWarranty = (product) => hasActiveWarranty(product, linkedInsurance(product))

// Kennzahlen je Kategorie. Archivierte Produkte (verkauft/kaputt) sind hier
// bewusst nicht enthalten; der Wert teilt sich stattdessen in mit/ohne Garantie.
function buildCategoryStats(products, values) {
  const byCategory = new Map()
  for (const p of products) {
    const key = categoryKey(p)
    let entry = byCategory.get(key)
    if (!entry) {
      entry = {
        kategorie: key,
        value: 0,
        warrantyValue: 0,
        count: 0,
        warrantyCount: 0,
        withoutReceipt: 0,
        assumedCount: 0,
      }
      byCategory.set(key, entry)
    }
    const value = values.get(p.id) || 0
    entry.value += value
    entry.count += 1
    if (underWarranty(p)) {
      entry.warrantyValue += value
      entry.warrantyCount += 1
    }
    if (!values.has(p.id)) entry.withoutReceipt += 1
    if (isWarrantyAssumed(p, linkedInsurance(p))) entry.assumedCount += 1
  }
  return [...byCategory.values()].sort(
    (a, b) => b.value - a.value || a.kategorie.localeCompare(b.kategorie, 'de')
  )
}

// Basis ist immer die aktive Produktliste — Archiviertes gehört dir nicht mehr
const allStats = computed(() => buildCategoryStats(activeItems.value, valueByProduct.value))
const scopedStats = computed(() => {
  if (breakdownScope.value === 'warranty') {
    return buildCategoryStats(activeItems.value.filter(underWarranty), valueByProduct.value)
  }
  if (breakdownScope.value === 'nowarranty') {
    return buildCategoryStats(
      activeItems.value.filter((p) => !underWarranty(p)),
      valueByProduct.value
    )
  }
  return allStats.value
})

// Ohne einen einzigen Belegbetrag hat die Auswertung nichts zu zeigen
const hasInventory = computed(() => allStats.value.some((s) => s.value > 0))
const breakdownTotal = computed(() => scopedStats.value.reduce((sum, s) => sum + s.value, 0))
const breakdownProductCount = computed(() => scopedStats.value.reduce((sum, s) => sum + s.count, 0))
const breakdownWithoutReceipt = computed(() =>
  scopedStats.value.reduce((sum, s) => sum + s.withoutReceipt, 0)
)
const breakdownAssumed = computed(() =>
  scopedStats.value.reduce((sum, s) => sum + s.assumedCount, 0)
)
const sharePercent = (stat) => (breakdownTotal.value ? (stat.value / breakdownTotal.value) * 100 : 0)

// Der Donut zeigt nur Kategorien mit Wert; ein 0-€-Segment wäre nicht darstellbar.
// Bei vielen Freitext-Kategorien wandert der lange Rest in ein Sammelsegment,
// das bewusst nicht filterbar ist — die Liste darunter bleibt vollständig.
const DONUT_MAX_SEGMENTS = 8
const donutEntries = computed(() => {
  const withValue = scopedStats.value.filter((s) => s.value > 0)
  const toEntry = (s) => ({ label: s.kategorie, value: s.value, kategorie: s.kategorie })
  if (withValue.length <= DONUT_MAX_SEGMENTS) return withValue.map(toEntry)
  const head = withValue.slice(0, DONUT_MAX_SEGMENTS - 1).map(toEntry)
  const rest = withValue.slice(DONUT_MAX_SEGMENTS - 1)
  return [
    ...head,
    {
      label: `Weitere (${rest.length})`,
      value: rest.reduce((sum, s) => sum + s.value, 0),
      kategorie: null,
    },
  ]
})
const donutSeries = computed(() => donutEntries.value.map((e) => Math.round(e.value * 100) / 100))
const chartTheme = useChartTheme()
const donutOptions = computed(() => ({
  ...chartTheme.value,
  labels: donutEntries.value.map((e) => e.label),
  legend: { ...chartTheme.value.legend, position: 'bottom' },
  chart: {
    ...chartTheme.value.chart,
    // Ohne das mountet der Chart mitten in der Ausklapp-Animation (Container noch
    // auf Höhe 0) und die Eintritts-Animation endet bei leeren Segment-Pfaden
    animations: { enabled: false },
    events: {
      // Klick/Tipp auf ein Segment filtert die Liste auf diese Kategorie
      dataPointSelection(_event, _ctx, { dataPointIndex }) {
        const entry = donutEntries.value[dataPointIndex]
        if (entry?.kategorie) toggleCategory(entry.kategorie)
      },
    },
  },
  // Absolute Euro-Werte auf den Segmenten statt Prozente (wie im Dashboard)
  dataLabels: {
    enabled: true,
    formatter: (val, opts) => formatCurrency(opts.w.globals.series[opts.seriesIndex]),
  },
  tooltip: { ...chartTheme.value.tooltip, y: { formatter: (val) => formatCurrency(val) } },
  plotOptions: {
    pie: {
      donut: {
        labels: {
          show: true,
          value: { formatter: (val) => formatCurrency(Number(val)) },
          total: {
            show: true,
            label: 'Gesamt',
            formatter: (w) => formatCurrency(w.globals.seriesTotals.reduce((a, b) => a + b, 0)),
          },
        },
      },
    },
  },
}))

function toggleCategory(kategorie) {
  categoryFilter.value = categoryFilter.value === kategorie ? null : kategorie
}

const filteredItems = computed(() => {
  const query = search.value.trim().toLowerCase()
  const pool = statusFilter.value === 'archived' ? items.value.filter((i) => i.archived) : activeItems.value
  return pool.filter((item) => {
    if (categoryFilter.value && categoryKey(item) !== categoryFilter.value) return false

    const insTitle = insurances.value.find((ins) => ins.id === item.linked_insurance_id)?.name || ''
    const matchesQuery = !query || [item.name, item.kategorie, insTitle]
      .filter(Boolean)
      .some((value) => value.toLowerCase().includes(query))
    if (!matchesQuery) return false

    const days = daysUntil(item.warranty_end)
    if (statusFilter.value === 'warning') return days != null && days >= 0 && days <= 90
    if (statusFilter.value === 'expired') return days != null && days < 0
    return true
  })
})
const expiringSoonCount = computed(() => activeItems.value.filter((item) => {
  const days = daysUntil(item.warranty_end)
  return days != null && days >= 0 && days <= 90
}).length)
const expiredCount = computed(() => activeItems.value.filter((item) => {
  const days = daysUntil(item.warranty_end)
  return days != null && days < 0
}).length)

// Aktive und archivierte Produkte stehen nie zusammen in der Liste. Trifft ein
// Kategorie-Filter nur Archiviertes, liefe die Liste sonst kommentarlos leer.
const archivedOnlyHint = computed(
  () =>
    Boolean(categoryFilter.value) &&
    !filteredItems.value.length &&
    statusFilter.value !== 'archived' &&
    // Nur wenn die Kategorie wirklich ausschließlich im Archiv liegt — sonst
    // ist schlicht der Status-Filter schuld, dass die Liste leer bleibt
    !activeItems.value.some((i) => categoryKey(i) === categoryFilter.value) &&
    items.value.some((i) => i.archived && categoryKey(i) === categoryFilter.value)
)
const emptyHeadline = computed(() =>
  archivedOnlyHint.value
    ? `Nur archivierte Produkte in „${categoryFilter.value}“`
    : 'Keine Produkte gefunden'
)
const emptyText = computed(() => {
  if (archivedOnlyHint.value) {
    return 'Diese Kategorie enthält nur archivierte Produkte — sie zählen zum Warenwert, stehen aber im Archiv.'
  }
  return search.value || categoryFilter.value
    ? 'Passe Suche oder Filter an.'
    : 'Lege Produkte an, um Garantiefristen automatisch im Blick zu behalten.'
})

// IDs aller Produkte mit mindestens einem Beleg (für den Datenqualitäts-Check)
const productIdsWithInvoices = computed(() => new Set(invoices.value.map((i) => i.product_id)))

function issuesFor(item) {
  return productQualityIssues(item, productIdsWithInvoices.value.has(item.id))
}

async function load() {
  try {
    const [products, allInsurances, allInvoices] = await Promise.all([
      productsApi.list(),
      insurancesApi.list(),
      invoicesApi.list(),
    ])
    items.value = products
    insurances.value = allInsurances
    invoices.value = allInvoices
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Laden fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  }
}

function openNew() {
  formTarget.value = null
  dialog.value = true
}

function goInvoices(item) {
  router.push({ path: '/invoices', query: { product: item.id } })
}
function openEdit(item) {
  formTarget.value = item
  dialog.value = true
}

async function onSaved() {
  snack.value = { show: true, color: 'success', text: 'Produkt gespeichert' }
  await load()
}
function confirmDelete(item) {
  deleteTarget.value = item
  deleteDialog.value = true
}

// Lösch-Undo: Eintrag verschwindet sofort, der API-Aufruf läuft erst nach 5 s —
// solange kann „Rückgängig" ihn abbrechen (analog zur Vertragsliste).
let pendingDelete = null

function flushPendingDelete() {
  if (!pendingDelete) return
  clearTimeout(pendingDelete.timer)
  const { item } = pendingDelete
  pendingDelete = null
  productsApi.delete(item.id).catch(() => {})
}

function onDelete() {
  deleteDialog.value = false
  const item = deleteTarget.value
  deleteTarget.value = null
  flushPendingDelete()
  items.value = items.value.filter((i) => i.id !== item.id)
  pendingDelete = {
    item,
    timer: setTimeout(async () => {
      pendingDelete = null
      try {
        await productsApi.delete(item.id)
      } catch (e) {
        snack.value = { show: true, color: 'error', text: 'Löschen fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
        await load()
      }
    }, 5000),
  }
  snack.value = { show: true, color: 'info', text: `„${item.name}" gelöscht.`, undo: true }
}

async function undoDelete() {
  if (!pendingDelete) return
  clearTimeout(pendingDelete.timer)
  pendingDelete = null
  snack.value = { show: true, color: 'success', text: 'Löschen rückgängig gemacht.' }
  await load()
}

onBeforeUnmount(flushPendingDelete)

onMounted(async () => {
  await load()
  initialLoading.value = false
})
</script>

<style scoped>
/* Donut-Segmente filtern die Liste (dataPointSelection) — Zeiger signalisiert das */
:deep(.apexcharts-pie-area) {
  cursor: pointer;
}
</style>
