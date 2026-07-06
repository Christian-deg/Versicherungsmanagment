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
      </v-col>
    </v-row>

    <v-skeleton-loader v-if="initialLoading" :type="smAndDown ? 'card' : 'table'" />

    <!-- Mobil: Karten -->
    <template v-else-if="smAndDown">
      <v-empty-state
        v-if="!filteredItems.length"
        headline="Keine Produkte gefunden"
        :text="search ? 'Passe Suche oder Filter an.' : 'Lege Produkte an, um Garantiefristen automatisch im Blick zu behalten.'"
        icon="mdi-package-variant-closed"
      >
        <template #actions>
          <v-btn color="primary" prepend-icon="mdi-plus" @click="openNew">Produkt anlegen</v-btn>
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
          headline="Keine Produkte gefunden"
          :text="search ? 'Passe Suche oder Filter an.' : 'Lege Produkte an, um Garantiefristen automatisch im Blick zu behalten.'"
          icon="mdi-package-variant-closed"
        >
          <template #actions>
            <v-btn color="primary" prepend-icon="mdi-plus" @click="openNew">Produkt anlegen</v-btn>
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
import { daysLabel, expiryColor, formatDate, daysUntil, persistedRef, productQualityIssues } from '../utils'

const route = useRoute()
const router = useRouter()
const { smAndDown } = useDisplay()
const items = ref([])
const insurances = ref([])
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

const filteredItems = computed(() => {
  const query = search.value.trim().toLowerCase()
  const pool = statusFilter.value === 'archived' ? items.value.filter((i) => i.archived) : activeItems.value
  return pool.filter((item) => {
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

// IDs aller Produkte mit mindestens einem Beleg (für den Datenqualitäts-Check)
const productIdsWithInvoices = ref(new Set())

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
    productIdsWithInvoices.value = new Set(allInvoices.map((i) => i.product_id))
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
