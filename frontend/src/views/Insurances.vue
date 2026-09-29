<template>
  <div>
    <div class="d-flex flex-column flex-md-row align-start align-md-center mb-4 ga-3">
      <div>
        <h1 class="text-h4">Versicherungen</h1>
        <p class="text-medium-emphasis mt-1">
          Suche schnell nach Verträgen, prüfe kritische Abläufe und bearbeite Stammdaten zentral.
        </p>
      </div>
      <v-spacer />
      <div class="d-flex flex-wrap ga-2">
        <v-btn color="primary" prepend-icon="mdi-plus" @click="openNew">Neu</v-btn>
        <v-btn variant="outlined" prepend-icon="mdi-file-pdf-box" :href="pdfUrl" target="_blank">PDF</v-btn>
        <v-btn variant="outlined" prepend-icon="mdi-file-excel" :href="xlsxUrl" target="_blank">Excel</v-btn>
      </div>
    </div>

    <v-row class="mb-1">
      <v-col cols="12" md="6">
        <v-text-field
          v-model="search"
          prepend-inner-icon="mdi-magnify"
          label="Nach Name, Kategorie, Versicherer oder Vertragsnummer suchen"
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
        <template v-if="personOptions.length">
          <v-divider vertical class="mx-1 d-none d-sm-block" />
          <v-chip
            v-for="p in personOptions"
            :key="p"
            :color="personFilter === p ? 'secondary' : undefined"
            prepend-icon="mdi-account"
            @click="personFilter = personFilter === p ? null : p"
          >
            {{ p }}
          </v-chip>
        </template>
      </v-col>
    </v-row>

    <v-skeleton-loader v-if="initialLoading" :type="smAndDown ? 'card' : 'table'" />

    <!-- Mobil: Karten -->
    <template v-else-if="smAndDown">
      <v-empty-state
        v-if="!filteredItems.length"
        headline="Keine Versicherungen gefunden"
        :text="search ? 'Passe Suche oder Filter an.' : 'Lege einen Vertrag manuell an oder starte mit einem Dokument-Upload.'"
        icon="mdi-shield-search"
      >
        <template #actions>
          <v-btn color="primary" prepend-icon="mdi-plus" @click="openNew">Manuell anlegen</v-btn>
          <v-btn variant="text" prepend-icon="mdi-cloud-upload" to="/upload">Dokument hochladen</v-btn>
        </template>
      </v-empty-state>
      <v-card v-for="item in filteredItems" :key="item.id" class="mb-3">
        <v-card-item>
          <v-card-title class="text-subtitle-1 text-wrap">
            <router-link :to="`/insurances/${item.id}`" class="text-decoration-none text-primary">
              {{ item.name }}
            </router-link>
          </v-card-title>
          <v-card-subtitle>{{ item.versicherer }} · Nr. {{ item.vertragsnummer }}</v-card-subtitle>
        </v-card-item>
        <v-card-text class="pt-0">
          <div class="d-flex flex-wrap ga-2 mb-2">
            <v-chip size="small" color="primary" :prepend-icon="categoryIcon(item.kategorie)">{{ item.kategorie }}</v-chip>
            <v-chip v-if="item.person" size="small" variant="tonal" prepend-icon="mdi-account">{{ item.person }}</v-chip>
            <v-chip size="small" :color="endColor(item.end_date)">
              {{ item.end_date ? `${formatDate(item.end_date)} · ${daysLabel(item.end_date)}` : 'Kein Enddatum' }}
            </v-chip>
            <v-chip
              v-if="trendFor(item)"
              size="small"
              :color="trendFor(item).pct > 0 ? 'error' : 'success'"
              variant="tonal"
              :prepend-icon="trendFor(item).pct > 0 ? 'mdi-trending-up' : 'mdi-trending-down'"
            >
              {{ trendLabel(item) }}
            </v-chip>
          </div>
          <div class="text-body-2">{{ formatEur(item.praemie_eur) }} / {{ item.zahlungsintervall }}</div>
          <div v-if="shareLabel(item)" class="text-caption text-medium-emphasis">{{ shareLabel(item) }}</div>
          <div v-if="getCancellationInfo(item)" class="text-body-2 mt-1">
            <v-icon size="small" :color="cancellationColor(item)">mdi-calendar-remove</v-icon>
            Kündbar bis {{ formatDate(getCancellationInfo(item).deadline) }}
            <span v-if="getCancellationInfo(item).wirksamZum" class="text-caption text-medium-emphasis">
              · endet dann {{ formatDate(getCancellationInfo(item).wirksamZum) }}
            </span>
          </div>
          <div v-for="issue in issuesFor(item)" :key="issue" class="text-caption text-warning mt-1">
            <v-icon size="x-small" icon="mdi-alert-circle-outline" /> {{ issue }}
          </div>
        </v-card-text>
        <v-card-actions class="pt-0">
          <v-btn size="small" variant="text" prepend-icon="mdi-lightbulb" @click="getRecommendation(item)">
            Empfehlung
          </v-btn>
          <v-spacer />
          <v-btn icon="mdi-paperclip" size="small" variant="text" @click="openDocs(item)" />
          <v-btn icon="mdi-pencil" size="small" variant="text" @click="openEdit(item)" />
          <v-btn icon="mdi-delete" size="small" variant="text" color="error" @click="confirmDelete(item)" />
        </v-card-actions>
      </v-card>
    </template>

    <!-- Desktop: Tabelle -->
    <v-data-table
      v-else
      :headers="headers"
      :items="filteredItems"
      :items-per-page="20"
      density="comfortable"
    >
      <template #item.name="{ item }">
        <router-link
          :to="`/insurances/${item.id}`"
          class="text-decoration-none text-primary font-weight-medium"
        >
          {{ item.name }}
        </router-link>
        <v-chip v-if="item.person" size="x-small" variant="tonal" prepend-icon="mdi-account" class="ml-1">
          {{ item.person }}
        </v-chip>
        <v-tooltip v-if="issuesFor(item).length" location="top">
          <template #activator="{ props }">
            <v-icon
              v-bind="props"
              icon="mdi-alert-circle-outline"
              color="warning"
              size="small"
              class="ml-1"
            />
          </template>
          <div v-for="issue in issuesFor(item)" :key="issue">• {{ issue }}</div>
        </v-tooltip>
      </template>
      <template #item.kategorie="{ item }">
        <v-chip size="small" color="primary" :prepend-icon="categoryIcon(item.kategorie)">
          {{ item.kategorie }}
        </v-chip>
      </template>
      <template #item.praemie_eur="{ item }">
        <div>{{ formatEur(item.praemie_eur) }} / {{ item.zahlungsintervall }}</div>
        <div v-if="shareLabel(item)" class="text-caption text-medium-emphasis">{{ shareLabel(item) }}</div>
        <v-chip
          v-if="trendFor(item)"
          size="x-small"
          :color="trendFor(item).pct > 0 ? 'error' : 'success'"
          variant="tonal"
          :prepend-icon="trendFor(item).pct > 0 ? 'mdi-trending-up' : 'mdi-trending-down'"
        >
          {{ trendLabel(item) }}
        </v-chip>
      </template>
      <template #item.end_date="{ item }">
        <v-chip size="small" :color="endColor(item.end_date)">
          {{ item.end_date ? `${formatDate(item.end_date)} · ${daysLabel(item.end_date)}` : '–' }}
        </v-chip>
      </template>
      <template #item.kuendigungsfrist="{ item }">
        <template v-if="getCancellationInfo(item)">
          <v-chip size="small" :color="cancellationColor(item)">
            bis {{ formatDate(getCancellationInfo(item).deadline) }}
          </v-chip>
          <div v-if="getCancellationInfo(item).wirksamZum" class="text-caption text-medium-emphasis">
            endet dann {{ formatDate(getCancellationInfo(item).wirksamZum) }}
          </div>
        </template>
        <span v-else class="text-medium-emphasis">–</span>
      </template>
      <template #item.actions="{ item }">
        <v-tooltip text="Dokumente verwalten" location="top">
          <template #activator="{ props }">
            <v-btn v-bind="props" icon="mdi-paperclip" size="small" variant="text" @click="openDocs(item)" />
          </template>
        </v-tooltip>
        <v-tooltip text="Bearbeiten" location="top">
          <template #activator="{ props }">
            <v-btn v-bind="props" icon="mdi-pencil" size="small" variant="text" @click="openEdit(item)" />
          </template>
        </v-tooltip>
        <v-tooltip text="KI-Empfehlung abrufen" location="top">
          <template #activator="{ props }">
            <v-btn v-bind="props" icon="mdi-lightbulb" size="small" variant="text" @click="getRecommendation(item)" />
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
          headline="Keine Versicherungen gefunden"
          :text="search ? 'Passe Suche oder Filter an.' : 'Lege einen Vertrag manuell an oder starte mit einem Dokument-Upload.'"
          icon="mdi-shield-search"
        >
          <template #actions>
            <v-btn color="primary" prepend-icon="mdi-plus" @click="openNew">Manuell anlegen</v-btn>
            <v-btn variant="text" prepend-icon="mdi-cloud-upload" to="/upload">Dokument hochladen</v-btn>
          </template>
        </v-empty-state>
      </template>
    </v-data-table>

    <InsuranceFormDialog v-model="dialog" :insurance="formTarget" @saved="onSaved" />

    <v-dialog v-model="recDialog" max-width="540" :fullscreen="smAndDown">
      <v-card>
        <v-card-title class="d-flex align-center">
          KI-Empfehlung
          <v-spacer />
          <v-btn v-if="smAndDown" icon="mdi-close" variant="text" @click="recDialog = false" />
        </v-card-title>
        <v-card-text>
          <div v-if="recLoading" class="text-center py-6">
            <v-progress-circular indeterminate color="primary" class="mb-3" />
            <div class="text-body-2 text-medium-emphasis">KI bewertet Versicherung…</div>
          </div>
          <template v-else-if="rec">
            <v-chip :color="recColor" class="mb-3">{{ rec.handlungsbedarf }}</v-chip>
            <p><strong>{{ rec.hinweis }}</strong></p>
            <p class="mt-2">{{ rec.details }}</p>
            <div class="text-caption text-medium-emphasis mt-3">
              Stand: {{ formatDate(rec.created_at) }} · wird jährlich automatisch erneuert
            </div>
          </template>
        </v-card-text>
        <v-card-actions>
          <v-btn
            variant="text"
            prepend-icon="mdi-refresh"
            :loading="recLoading"
            @click="regenerateRecommendation"
          >
            Neu bewerten
          </v-btn>
          <v-spacer />
          <v-btn @click="recDialog = false">Schließen</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Dokumente-Dialog: Unterlagen ansehen, jährlich neue ergänzen -->
    <v-dialog v-model="docDialog" max-width="640" :fullscreen="smAndDown">
      <v-card>
        <v-card-title class="d-flex align-center">
          <span class="text-truncate">Dokumente – {{ docTarget?.name }}</span>
          <v-spacer />
          <v-btn v-if="smAndDown" icon="mdi-close" variant="text" @click="docDialog = false" />
        </v-card-title>
        <v-card-text>
          <p class="text-body-2 text-medium-emphasis mb-3">
            Hier kannst du jederzeit neue Unterlagen ergänzen, z.&thinsp;B. die jährliche
            Beitragsrechnung. Neue Dokumente werden automatisch volltextindiziert und sind
            danach im Assistenten auffindbar.
          </p>
          <div class="d-flex flex-column flex-sm-row ga-2 align-sm-center mb-4">
            <v-file-input
              v-model="newDocFiles"
              label="Neue Dokumente (PDF, PNG, JPG)"
              accept="application/pdf,image/png,image/jpeg"
              multiple
              density="comfortable"
              hide-details
              prepend-icon="mdi-paperclip"
              :disabled="attaching"
            />
            <v-btn
              color="primary"
              :loading="attaching"
              :disabled="!hasNewDocFiles || attaching"
              @click="attachDocs"
            >
              Hinzufügen
            </v-btn>
          </div>

          <v-skeleton-loader v-if="docsLoading" type="list-item-two-line" />
          <v-list v-else-if="docs.length" lines="two" density="compact">
            <v-list-item v-for="d in docs" :key="d.id">
              <template #prepend>
                <v-icon :icon="d.mime_type === 'application/pdf' ? 'mdi-file-pdf-box' : 'mdi-file-image'" />
              </template>
              <v-list-item-title class="text-wrap">{{ d.original_filename }}</v-list-item-title>
              <v-list-item-subtitle>
                Hochgeladen am {{ formatDate(d.uploaded_at) }}<template v-if="d.ai_summary"> · KI-analysiert</template>
              </v-list-item-subtitle>
              <template #append>
                <v-btn
                  icon="mdi-open-in-new"
                  size="small"
                  variant="text"
                  aria-label="Dokument ansehen"
                  :href="`/api/documents/${d.id}/file`"
                  target="_blank"
                />
                <v-btn icon="mdi-delete" size="small" variant="text" color="error" @click="confirmDocDelete(d)" />
              </template>
            </v-list-item>
          </v-list>
          <v-empty-state
            v-else
            headline="Noch keine Dokumente"
            text="Füge die Police oder Beitragsrechnungen hinzu — sie werden für den Assistenten durchsuchbar."
            icon="mdi-file-document-outline"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="docDialog = false">Schließen</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Bestätigungs-Dialog: einzelnes Dokument löschen -->
    <v-dialog v-model="docDeleteDialog" max-width="420">
      <v-card>
        <v-card-title>Dokument löschen</v-card-title>
        <v-card-text>
          Möchtest du das Dokument <strong>„{{ docDeleteTarget?.original_filename }}"</strong> wirklich
          löschen? Datei und Suchindex-Einträge werden entfernt.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="docDeleteDialog = false">Abbrechen</v-btn>
          <v-btn color="error" @click="onDocDelete">Löschen</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Bestätigungs-Dialog für Löschen -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title>Versicherung löschen</v-card-title>
        <v-card-text>
          Möchtest du die Versicherung <strong>„{{ deleteTarget?.name }}"</strong> wirklich löschen?
          <v-alert type="warning" variant="tonal" density="compact" class="mt-3">
            Alle zugehörigen Dokumente und KI-Daten werden ebenfalls gelöscht. Verknüpfte
            Produkte bleiben erhalten und verlieren nur die Verknüpfung. Diese Aktion kann
            nicht rückgängig gemacht werden.
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
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'
import { insurancesApi, documentsApi } from '../api'
import InsuranceFormDialog from '../components/InsuranceFormDialog.vue'
import { categoryIcon } from '../constants'
import {
  daysLabel,
  daysUntil,
  expiryColor,
  formatCurrency,
  formatDate,
  getCancellationInfo,
  persistedRef,
  premiumTrend,
  qualityIssues,
  yearlyPremium,
} from '../utils'

const route = useRoute()
const router = useRouter()
const { smAndDown } = useDisplay()
const items = ref([])
const dialog = ref(false)
const recDialog = ref(false)
const rec = ref(null)
const recLoading = ref(false)
const recTarget = ref(null)
const formTarget = ref(null)
const snack = ref({ show: false, color: 'success', text: '' })
const search = ref('')
// Filterwahl überlebt Seitenwechsel und Neustarts
const statusFilter = persistedRef('versicherung-filter-insurances', 'all')
const personFilter = persistedRef('versicherung-filter-person', null)
const initialLoading = ref(true)
const deleteDialog = ref(false)
const deleteTarget = ref(null)
const docDialog = ref(false)
const docTarget = ref(null)
const docs = ref([])
const docsLoading = ref(false)
const newDocFiles = ref([])
const attaching = ref(false)
const docDeleteDialog = ref(false)
const docDeleteTarget = ref(null)

const headers = [
  { title: 'Name', key: 'name' },
  { title: 'Kategorie', key: 'kategorie' },
  { title: 'Versicherer', key: 'versicherer' },
  { title: 'Prämie', key: 'praemie_eur' },
  { title: 'Ende', key: 'end_date' },
  { title: 'Kündigung', key: 'kuendigungsfrist', sortable: false },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]

function cancellationColor(item) {
  const info = getCancellationInfo(item)
  if (!info) return 'grey'
  const days = daysUntil(info.deadline)
  if (days <= 14) return 'error'
  if (days <= 60) return 'warning'
  return 'success'
}

const pdfUrl = '/api/exports/insurances.pdf'
const xlsxUrl = '/api/exports/insurances.xlsx'

const recColor = computed(() => ({ keiner: 'success', pruefen: 'warning', handeln: 'error' })[rec.value?.handlungsbedarf?.toLowerCase?.()] || 'grey')
const formatEur = formatCurrency
const endColor = expiryColor
// Vorhandene Personen-Labels für die Filter-Chips
const personOptions = computed(() =>
  [...new Set(items.value.map((i) => i.person).filter(Boolean))].sort()
)

const filteredItems = computed(() => {
  const query = search.value.trim().toLowerCase()
  return items.value.filter((item) => {
    if (personFilter.value && item.person !== personFilter.value) return false
    const matchesQuery = !query || [item.name, item.kategorie, item.versicherer, item.vertragsnummer, item.person]
      .filter(Boolean)
      .some((value) => value.toLowerCase().includes(query))
    if (!matchesQuery) return false

    const days = daysUntil(item.end_date)
    if (statusFilter.value === 'warning') return days != null && days >= 0 && days <= 90
    if (statusFilter.value === 'expired') return days != null && days < 0
    return true
  })
})
const expiringSoonCount = computed(() => items.value.filter((item) => {
  const days = daysUntil(item.end_date)
  return days != null && days >= 0 && days <= 90
}).length)
const expiredCount = computed(() => items.value.filter((item) => {
  const days = daysUntil(item.end_date)
  return days != null && days < 0
}).length)
// Summe aller Jahresprämien — Basis für den Kostenanteil je Vertrag
const totalYearly = computed(() =>
  items.value.reduce((sum, i) => sum + (yearlyPremium(i) ?? 0), 0)
)

// "600 € p.a. · 12 % der Gesamtkosten" — leer, wenn keine Prämie bekannt
function shareLabel(item) {
  const yearly = yearlyPremium(item)
  if (yearly == null || yearly <= 0) return ''
  let label = `${formatCurrency(yearly)} p.a.`
  if (totalYearly.value > 0) {
    label += ` · ${Math.round((yearly / totalYearly.value) * 100)} % der Gesamtkosten`
  }
  return label
}

// IDs aller Versicherungen, die mindestens ein Dokument haben (für den Datenqualitäts-Check)
const insuranceIdsWithDocs = ref(new Set())
// Prämienverlauf je Versicherung (für den Trend-Chip)
const historyByInsurance = ref({})

function issuesFor(item) {
  return qualityIssues(item, insuranceIdsWithDocs.value.has(item.id))
}

function trendFor(item) {
  return premiumTrend(historyByInsurance.value[item.id])
}

function trendLabel(item) {
  const t = trendFor(item)
  return t ? `${t.pct > 0 ? '+' : ''}${t.pct} % seit ${t.sinceYear}` : ''
}

async function load() {
  try {
    const [insurances, allDocs, history] = await Promise.all([
      insurancesApi.list(),
      documentsApi.list(),
      insurancesApi.premiumHistory(),
    ])
    items.value = insurances
    insuranceIdsWithDocs.value = new Set(allDocs.filter((d) => d.insurance_id != null).map((d) => d.insurance_id))
    const grouped = {}
    for (const h of history) {
      ;(grouped[h.insurance_id] ??= []).push(h)
    }
    historyByInsurance.value = grouped
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Laden fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  }
}

function openNew() {
  formTarget.value = null
  dialog.value = true
}
function openEdit(item) {
  formTarget.value = item
  dialog.value = true
}
async function onSaved() {
  snack.value = { show: true, color: 'success', text: 'Versicherung gespeichert' }
  await load()
}
function confirmDelete(item) {
  deleteTarget.value = item
  deleteDialog.value = true
}

// Lösch-Undo: Eintrag verschwindet sofort aus der Liste, der API-Aufruf läuft
// erst nach 5 s — solange kann „Rückgängig" ihn abbrechen. Beim Verlassen der
// Seite wird eine ausstehende Löschung sofort ausgeführt.
let pendingDelete = null

function flushPendingDelete() {
  if (!pendingDelete) return
  clearTimeout(pendingDelete.timer)
  const { item } = pendingDelete
  pendingDelete = null
  insurancesApi.delete(item.id).catch(() => {})
}

function onDelete() {
  deleteDialog.value = false
  const item = deleteTarget.value
  deleteTarget.value = null
  flushPendingDelete() // vorherige ausstehende Löschung zuerst ausführen
  items.value = items.value.filter((i) => i.id !== item.id)
  pendingDelete = {
    item,
    timer: setTimeout(async () => {
      pendingDelete = null
      try {
        await insurancesApi.delete(item.id)
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
const hasNewDocFiles = computed(() => {
  const f = newDocFiles.value
  return Array.isArray(f) ? f.length > 0 : Boolean(f)
})

async function openDocs(item) {
  docTarget.value = item
  docs.value = []
  newDocFiles.value = []
  docDialog.value = true
  docsLoading.value = true
  try {
    docs.value = await documentsApi.list(item.id)
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Dokumente laden fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  } finally {
    docsLoading.value = false
  }
}

async function attachDocs() {
  const f = newDocFiles.value
  const list = (Array.isArray(f) ? f : [f]).filter(Boolean)
  if (!list.length) return
  attaching.value = true
  try {
    const results = await Promise.allSettled(list.map(file => documentsApi.attach(docTarget.value.id, file)))
    const failed = results.filter(r => r.status === 'rejected')
    if (failed.length) {
      const detail = failed[0].reason?.response?.data?.detail
      snack.value = {
        show: true,
        color: 'warning',
        text: `${failed.length} von ${list.length} Dokument(en) fehlgeschlagen${detail ? ': ' + detail : '.'}`,
      }
    } else {
      snack.value = {
        show: true,
        color: 'success',
        text: list.length === 1 ? 'Dokument hinzugefügt.' : `${list.length} Dokumente hinzugefügt.`,
      }
    }
    newDocFiles.value = []
    docs.value = await documentsApi.list(docTarget.value.id)
    syncDocFlag(docTarget.value.id, docs.value.length > 0)
  } finally {
    attaching.value = false
  }
}

// Dokument-Status für den Datenqualitäts-Check aktuell halten (Set klonen für Reaktivität)
function syncDocFlag(insuranceId, hasDocs) {
  const next = new Set(insuranceIdsWithDocs.value)
  if (hasDocs) next.add(insuranceId)
  else next.delete(insuranceId)
  insuranceIdsWithDocs.value = next
}

function confirmDocDelete(d) {
  docDeleteTarget.value = d
  docDeleteDialog.value = true
}

async function onDocDelete() {
  docDeleteDialog.value = false
  try {
    await documentsApi.delete(docDeleteTarget.value.id)
    docs.value = await documentsApi.list(docTarget.value.id)
    syncDocFlag(docTarget.value.id, docs.value.length > 0)
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Löschen fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  } finally {
    docDeleteTarget.value = null
  }
}

async function getRecommendation(item) {
  recTarget.value = item
  rec.value = null
  recLoading.value = true
  recDialog.value = true
  try {
    // Zuerst gespeicherte Empfehlung laden; falls noch keine existiert, neu erzeugen
    rec.value = await documentsApi.recommendationGet(item.id)
    if (!rec.value) {
      rec.value = await documentsApi.recommendation(item.id)
    }
  } catch (e) {
    recDialog.value = false
    snack.value = { show: true, color: 'error', text: 'Empfehlung fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  } finally {
    recLoading.value = false
  }
}

async function regenerateRecommendation() {
  if (!recTarget.value) return
  recLoading.value = true
  try {
    rec.value = await documentsApi.recommendation(recTarget.value.id)
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Empfehlung fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  } finally {
    recLoading.value = false
  }
}

onMounted(async () => {
  await load()
  initialLoading.value = false
  if (route.query.saved === '1') {
    snack.value = { show: true, color: 'success', text: 'Versicherung gespeichert' }
    router.replace({ path: '/insurances' })
  }
})
</script>
