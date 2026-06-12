<template>
  <div>
    <div class="d-flex flex-column flex-md-row align-start align-md-center mb-4 ga-3">
      <div>
        <h1 class="text-h4">Rechnungen & Kaufbelege</h1>
        <p class="text-medium-emphasis mt-1">
          Rechnungen werden mindestens 2 Jahre aufbewahrt – bei längerer Garantie automatisch bis zum Garantieende.
        </p>
      </div>
      <v-spacer />
      <v-btn color="primary" prepend-icon="mdi-upload" :block="smAndDown" @click="openUpload">
        Rechnung hochladen
      </v-btn>
    </div>

    <!-- Filter-Zeile -->
    <v-row class="mb-2">
      <v-col cols="12" md="5">
        <v-text-field
          v-model="search"
          prepend-inner-icon="mdi-magnify"
          label="Produkt oder Dateiname suchen"
          variant="outlined"
          density="comfortable"
          hide-details
        />
      </v-col>
      <v-col cols="12" md="7" class="d-flex flex-wrap align-center ga-2">
        <v-chip :color="retainFilter === 'all' ? 'primary' : undefined" @click="retainFilter = 'all'">Alle {{ items.length }}</v-chip>
        <v-chip :color="retainFilter === 'expiring' ? 'warning' : undefined" @click="retainFilter = 'expiring'">
          Frist bald (&lt; 6 Monate) ({{ expiringCount }})
        </v-chip>
        <v-chip :color="retainFilter === 'expired' ? 'error' : undefined" @click="retainFilter = 'expired'">
          Löschbar ({{ expiredCount }})
        </v-chip>
        <v-chip
          v-if="productFilter"
          color="secondary"
          closable
          @click:close="clearProductFilter"
        >
          Produkt: {{ productName(productFilter) }}
        </v-chip>
      </v-col>
    </v-row>

    <v-skeleton-loader v-if="initialLoading" :type="smAndDown ? 'card' : 'table'" />

    <!-- Mobil: Karten -->
    <template v-else-if="smAndDown">
      <v-empty-state
        v-if="!filteredItems.length"
        headline="Keine Rechnungen gefunden"
        :text="search || productFilter ? 'Passe Suche oder Filter an.' : 'Lade Rechnungen hoch, um Garantiebelege sicher zu archivieren.'"
        icon="mdi-receipt-text-outline"
      >
        <template #actions>
          <v-btn color="primary" prepend-icon="mdi-upload" @click="openUpload">Rechnung hochladen</v-btn>
        </template>
      </v-empty-state>
      <v-card v-for="item in filteredItems" :key="item.id" class="mb-3">
        <v-card-item>
          <v-card-title class="text-subtitle-1 text-wrap">{{ item.original_filename }}</v-card-title>
          <v-card-subtitle>{{ productName(item.product_id) }}</v-card-subtitle>
        </v-card-item>
        <v-card-text class="pt-0">
          <v-chip size="small" :color="retainColor(item.retain_until)" class="mb-2">
            {{ formatDate(item.retain_until) }} · {{ retainLabel(item.retain_until) }}
          </v-chip>
          <div class="text-body-2">
            Kaufdatum: {{ item.purchase_date ? formatDate(item.purchase_date) : '–' }}
            · Betrag: {{ item.amount_eur != null ? formatCurrency(item.amount_eur) : '–' }}
          </div>
          <div v-if="item.notes" class="text-body-2 text-medium-emphasis mt-1">{{ item.notes }}</div>
        </v-card-text>
        <v-card-actions class="pt-0">
          <span v-if="!canDelete(item.retain_until)" class="text-caption text-medium-emphasis">
            Aufbewahrung bis {{ formatDate(item.retain_until) }}
          </span>
          <v-spacer />
          <v-btn
            icon="mdi-delete"
            size="small"
            variant="text"
            :color="canDelete(item.retain_until) ? 'error' : 'grey'"
            :disabled="!canDelete(item.retain_until)"
            @click="confirmDelete(item)"
          />
        </v-card-actions>
      </v-card>
    </template>

    <!-- Desktop: Tabelle -->
    <v-data-table v-else :headers="headers" :items="filteredItems" :items-per-page="20">
      <template #item.product_id="{ item }">
        <span>{{ productName(item.product_id) }}</span>
      </template>
      <template #item.purchase_date="{ item }">
        {{ item.purchase_date ? formatDate(item.purchase_date) : '–' }}
      </template>
      <template #item.amount_eur="{ item }">
        {{ item.amount_eur != null ? formatCurrency(item.amount_eur) : '–' }}
      </template>
      <template #item.retain_until="{ item }">
        <v-chip size="small" :color="retainColor(item.retain_until)">
          {{ formatDate(item.retain_until) }} · {{ retainLabel(item.retain_until) }}
        </v-chip>
      </template>
      <template #item.actions="{ item }">
        <v-tooltip :text="canDelete(item.retain_until) ? 'Löschen' : `Aufbewahrung bis ${formatDate(item.retain_until)}`" location="top">
          <template #activator="{ props }">
            <v-btn
              v-bind="props"
              icon="mdi-delete"
              size="small"
              variant="text"
              :color="canDelete(item.retain_until) ? 'error' : 'grey'"
              :disabled="!canDelete(item.retain_until)"
              @click="confirmDelete(item)"
            />
          </template>
        </v-tooltip>
      </template>
      <template #no-data>
        <v-empty-state
          headline="Keine Rechnungen gefunden"
          :text="search || productFilter ? 'Passe Suche oder Filter an.' : 'Lade Rechnungen hoch, um Garantiebelege sicher zu archivieren.'"
          icon="mdi-receipt-text-outline"
        >
          <template #actions>
            <v-btn color="primary" prepend-icon="mdi-upload" @click="openUpload">Rechnung hochladen</v-btn>
          </template>
        </v-empty-state>
      </template>
    </v-data-table>

    <!-- Upload-Dialog -->
    <v-dialog v-model="uploadDialog" max-width="560" :fullscreen="smAndDown">
      <v-card>
        <v-card-title class="d-flex align-center">
          {{ uploadStep === 1 ? 'Rechnung hochladen' : 'Extrahierte Daten prüfen' }}
          <v-spacer />
          <v-btn v-if="smAndDown" icon="mdi-close" variant="text" @click="uploadDialog = false" />
        </v-card-title>

        <!-- Schritt 1: Datei + Produkt -->
        <v-card-text v-if="uploadStep === 1">
          <p class="text-body-2 text-medium-emphasis mb-4">
            Datei hochladen – die KI liest Kaufdatum und Betrag automatisch aus.
          </p>
          <v-select
            v-model="form.product_id"
            :items="productOptions"
            label="Produkt *"
            required
          />
          <v-file-input
            v-model="form.file"
            label="Datei (PDF, PNG, JPG) *"
            accept=".pdf,.png,.jpg,.jpeg"
            prepend-icon="mdi-paperclip"
          />
        </v-card-text>
        <v-card-actions v-if="uploadStep === 1">
          <v-spacer />
          <v-btn @click="uploadDialog = false">Abbrechen</v-btn>
          <v-btn
            color="primary"
            :loading="analyzing"
            :disabled="!form.product_id || !form.file || analyzing"
            @click="doAnalyze"
            prepend-icon="mdi-robot"
          >
            {{ analyzing ? 'KI analysiert…' : 'Analysieren' }}
          </v-btn>
        </v-card-actions>

        <!-- Schritt 2: Extrahierte Felder bestätigen -->
        <v-card-text v-if="uploadStep === 2">
          <v-alert type="info" variant="tonal" density="compact" class="mb-4">
            KI-Vorschlag – bitte prüfen und bei Bedarf korrigieren.
          </v-alert>
          <v-row>
            <v-col cols="12" sm="6">
              <v-text-field v-model="form.purchase_date" label="Kaufdatum" type="date" />
            </v-col>
            <v-col cols="12" sm="6">
              <v-text-field v-model="form.amount_eur" label="Betrag (€)" type="number" min="0" step="0.01" />
            </v-col>
          </v-row>
          <v-textarea v-model="form.notes" label="Notizen (Händler / Produkt)" rows="2" />
          <v-alert v-if="retainPreview" type="info" variant="tonal" class="mt-2" density="compact">
            Aufbewahrung bis: <strong>{{ retainPreview }}</strong>
          </v-alert>
        </v-card-text>
        <v-card-actions v-if="uploadStep === 2">
          <v-btn @click="uploadStep = 1" prepend-icon="mdi-arrow-left">Zurück</v-btn>
          <v-spacer />
          <v-btn color="primary" :loading="uploading" :disabled="uploading" @click="doUpload">
            Hochladen
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Löschen-Bestätigung -->
    <v-dialog v-model="deleteDialog" max-width="420">
      <v-card>
        <v-card-title>Rechnung löschen</v-card-title>
        <v-card-text>
          Möchtest du die Rechnung <strong>„{{ deleteTarget?.original_filename }}"</strong> wirklich löschen?
          Diese Aktion kann nicht rückgängig gemacht werden.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="deleteDialog = false">Abbrechen</v-btn>
          <v-btn color="error" @click="doDelete">Löschen</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snack.show" :color="snack.color">{{ snack.text }}</v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'
import { invoicesApi, productsApi } from '../api'
import { formatDate, formatCurrency, daysUntil } from '../utils'

const route = useRoute()
const router = useRouter()
const { smAndDown } = useDisplay()

const items = ref([])
const products = ref([])
const initialLoading = ref(true)
const search = ref('')
const retainFilter = ref('all')
const productFilter = ref(null)
const uploadDialog = ref(false)
const deleteDialog = ref(false)
const deleteTarget = ref(null)
const uploading = ref(false)
const analyzing = ref(false)
const uploadStep = ref(1)
const snack = ref({ show: false, color: 'success', text: '' })

const form = ref({ product_id: null, file: null, purchase_date: '', amount_eur: '', notes: '' })

const headers = [
  { title: 'Produkt', key: 'product_id' },
  { title: 'Datei', key: 'original_filename' },
  { title: 'Kaufdatum', key: 'purchase_date' },
  { title: 'Betrag', key: 'amount_eur' },
  { title: 'Aufbewahrung bis', key: 'retain_until' },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]

const productOptions = computed(() =>
  products.value.map((p) => ({ title: `${p.name} (${p.kategorie})`, value: p.id }))
)

function productName(id) {
  const p = products.value.find((p) => p.id === id)
  return p ? p.name : `Produkt #${id}`
}

function canDelete(retainUntil) {
  // Backend erlaubt Löschen, sobald retain_until erreicht ist (heute eingeschlossen)
  const days = daysUntil(retainUntil)
  return days != null && days <= 0
}

function retainColor(retainUntil) {
  const days = daysUntil(retainUntil)
  if (days == null) return 'grey'
  if (days <= 0) return 'grey'
  if (days < 30) return 'error'
  if (days < 180) return 'warning'
  return 'success'
}

function retainLabel(retainUntil) {
  const days = daysUntil(retainUntil)
  if (days == null) return ''
  if (days <= 0) return 'löschbar'
  if (days === 1) return 'noch 1 Tag'
  return `noch ${days} Tage`
}

const expiringCount = computed(() =>
  items.value.filter((i) => { const d = daysUntil(i.retain_until); return d != null && d > 0 && d < 180 }).length
)
const expiredCount = computed(() =>
  items.value.filter((i) => canDelete(i.retain_until)).length
)

const filteredItems = computed(() => {
  const q = search.value.trim().toLowerCase()
  return items.value.filter((item) => {
    if (productFilter.value && item.product_id !== productFilter.value) return false
    const pname = productName(item.product_id).toLowerCase()
    const matchesQuery = !q || [item.original_filename, pname].some((v) => v.toLowerCase().includes(q))
    if (!matchesQuery) return false
    const days = daysUntil(item.retain_until)
    if (retainFilter.value === 'expiring') return days != null && days > 0 && days < 180
    if (retainFilter.value === 'expired') return canDelete(item.retain_until)
    return true
  })
})

// Vorschau der Aufbewahrungsfrist beim Upload berechnen
const retainPreview = computed(() => {
  if (!form.value.product_id || !form.value.purchase_date) return null
  const product = products.value.find((p) => p.id === form.value.product_id)
  if (!product) return null
  const pd = new Date(form.value.purchase_date)
  const minRetain = new Date(pd)
  minRetain.setDate(minRetain.getDate() + 730)
  let retain = minRetain
  if (product.warranty_end) {
    const we = new Date(product.warranty_end)
    if (we > retain) retain = we
  }
  return formatDate(retain.toISOString().slice(0, 10))
})

function clearProductFilter() {
  productFilter.value = null
  router.replace({ path: '/invoices' })
}

async function load() {
  try {
    [items.value, products.value] = await Promise.all([invoicesApi.list(), productsApi.list()])
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Laden fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  }
}

function openUpload() {
  form.value = {
    product_id: productFilter.value || null,
    file: null,
    purchase_date: '',
    amount_eur: '',
    notes: '',
  }
  uploadStep.value = 1
  uploadDialog.value = true
}

async function doAnalyze() {
  analyzing.value = true
  try {
    const file = Array.isArray(form.value.file) ? form.value.file[0] : form.value.file
    const result = await invoicesApi.analyze(file)
    form.value.purchase_date = result.purchase_date || ''
    form.value.amount_eur = result.amount_eur != null ? result.amount_eur : ''
    form.value.notes = result.notes || ''
    uploadStep.value = 2
  } catch (e) {
    // Analyse fehlgeschlagen → trotzdem zu Schritt 2, Felder leer
    form.value.purchase_date = ''
    form.value.amount_eur = ''
    form.value.notes = ''
    uploadStep.value = 2
    snack.value = { show: true, color: 'warning', text: 'KI-Analyse nicht möglich – bitte Felder manuell ausfüllen.' }
  } finally {
    analyzing.value = false
  }
}

async function doUpload() {
  uploading.value = true
  try {
    const file = Array.isArray(form.value.file) ? form.value.file[0] : form.value.file
    await invoicesApi.upload(form.value.product_id, file, {
      purchaseDate: form.value.purchase_date || undefined,
      amountEur: form.value.amount_eur ? parseFloat(form.value.amount_eur) : undefined,
      notes: form.value.notes || undefined,
    })
    uploadDialog.value = false
    snack.value = { show: true, color: 'success', text: 'Rechnung erfolgreich hochgeladen.' }
    await load()
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Upload fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  } finally {
    uploading.value = false
  }
}

function confirmDelete(item) {
  deleteTarget.value = item
  deleteDialog.value = true
}

async function doDelete() {
  deleteDialog.value = false
  try {
    await invoicesApi.delete(deleteTarget.value.id)
    snack.value = { show: true, color: 'success', text: 'Rechnung gelöscht.' }
    await load()
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Löschen fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  } finally {
    deleteTarget.value = null
  }
}

onMounted(async () => {
  const fromQuery = Number(route.query.product)
  if (Number.isInteger(fromQuery) && fromQuery > 0) {
    productFilter.value = fromQuery
  }
  await load()
  initialLoading.value = false
  if (route.query.upload === '1') {
    openUpload()
  }
})
</script>
