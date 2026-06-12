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
        <v-chip :color="statusFilter === 'all' ? 'primary' : undefined" @click="statusFilter = 'all'">Alle {{ items.length }}</v-chip>
        <v-chip :color="statusFilter === 'warning' ? 'warning' : undefined" @click="statusFilter = 'warning'">
          Läuft bald ab ({{ expiringSoonCount }})
        </v-chip>
        <v-chip :color="statusFilter === 'expired' ? 'error' : undefined" @click="statusFilter = 'expired'">
          Abgelaufen ({{ expiredCount }})
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
          <v-card-title class="text-subtitle-1 text-wrap">{{ item.name }}</v-card-title>
          <v-card-subtitle>{{ item.kategorie }}</v-card-subtitle>
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

    <v-dialog v-model="dialog" max-width="600" :fullscreen="smAndDown">
      <v-card>
        <v-card-title class="d-flex align-center">
          {{ editing.id ? 'Produkt bearbeiten' : 'Neues Produkt' }}
          <v-spacer />
          <v-btn v-if="smAndDown" icon="mdi-close" variant="text" @click="dialog = false" />
        </v-card-title>
        <v-card-text>
          <p class="text-body-2 text-medium-emphasis mb-4">
            Ein Garantieende hilft dir, rechtzeitig vor Ablauf erinnert zu werden.
          </p>
          <v-text-field v-model="editing.name" label="Name" required />
          <v-text-field v-model="editing.kategorie" label="Kategorie (frei)" />
          <v-row>
            <v-col cols="12" sm="6"><v-text-field v-model="editing.purchase_date" label="Kaufdatum" type="date" /></v-col>
            <v-col cols="12" sm="6"><v-text-field v-model="editing.warranty_end" label="Garantieende" type="date" /></v-col>
          </v-row>
          <v-select v-model="editing.linked_insurance_id" :items="insuranceOptions" label="Verknüpfte Versicherung (optional)" clearable />
          <v-textarea v-model="editing.notes" label="Notizen" rows="2" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="dialog = false">Abbrechen</v-btn>
          <v-btn color="primary" :disabled="!editing.name" @click="save">Speichern</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

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

    <v-snackbar v-model="snack.show" :color="snack.color">{{ snack.text }}</v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'
import { productsApi, insurancesApi } from '../api'
import { daysLabel, expiryColor, formatDate, daysUntil } from '../utils'

const router = useRouter()
const { smAndDown } = useDisplay()
const items = ref([])
const insurances = ref([])
const dialog = ref(false)
const editing = ref({})
const snack = ref({ show: false, color: 'success', text: '' })
const search = ref('')
const statusFilter = ref('all')
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

const insuranceOptions = computed(() =>
  insurances.value.map((i) => ({ title: `${i.name} (${i.versicherer})`, value: i.id }))
)

function insuranceName(id) {
  const ins = insurances.value.find((i) => i.id === id)
  return ins ? `${ins.name} (${ins.versicherer})` : `ID ${id}`
}

const endColor = expiryColor
const filteredItems = computed(() => {
  const query = search.value.trim().toLowerCase()
  return items.value.filter((item) => {
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
const expiringSoonCount = computed(() => items.value.filter((item) => {
  const days = daysUntil(item.warranty_end)
  return days != null && days >= 0 && days <= 90
}).length)
const expiredCount = computed(() => items.value.filter((item) => {
  const days = daysUntil(item.warranty_end)
  return days != null && days < 0
}).length)
async function load() {
  try {
    items.value = await productsApi.list()
    insurances.value = await insurancesApi.list()
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Laden fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  }
}

function openNew() {
  editing.value = { name: '', kategorie: '', notes: '', linked_insurance_id: null }
  dialog.value = true
}

// Kaufdatum geändert → Garantieende automatisch auf +2 Jahre setzen (nur wenn noch leer)
watch(
  () => editing.value.purchase_date,
  (newDate) => {
    if (!newDate || editing.value.warranty_end) return
    const d = new Date(newDate)
    d.setFullYear(d.getFullYear() + 2)
    editing.value.warranty_end = d.toISOString().slice(0, 10)
  }
)

function goInvoices(item) {
  router.push({ path: '/invoices', query: { product: item.id } })
}
function openEdit(item) { editing.value = { ...item }; dialog.value = true }

async function save() {
  try {
    const payload = { ...editing.value }
    delete payload.created_at
    // '' (geleertes Datumsfeld) → null, sonst lehnt das Backend mit 422 ab
    if (payload.purchase_date === '') payload.purchase_date = null
    if (payload.warranty_end === '') payload.warranty_end = null
    if (editing.value.id) {
      await productsApi.update(editing.value.id, payload)
    } else {
      await productsApi.create(payload)
    }
    dialog.value = false
    await load()
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Speichern fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  }
}
function confirmDelete(item) {
  deleteTarget.value = item
  deleteDialog.value = true
}
async function onDelete() {
  deleteDialog.value = false
  try {
    await productsApi.delete(deleteTarget.value.id)
    await load()
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Löschen fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  } finally {
    deleteTarget.value = null
  }
}

onMounted(async () => {
  await load()
  initialLoading.value = false
})
</script>
