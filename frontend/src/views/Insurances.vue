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
          <v-card-title class="text-subtitle-1 text-wrap">{{ item.name }}</v-card-title>
          <v-card-subtitle>{{ item.versicherer }} · Nr. {{ item.vertragsnummer }}</v-card-subtitle>
        </v-card-item>
        <v-card-text class="pt-0">
          <div class="d-flex flex-wrap ga-2 mb-2">
            <v-chip size="small" color="primary">{{ item.kategorie }}</v-chip>
            <v-chip size="small" :color="endColor(item.end_date)">
              {{ item.end_date ? `${formatDate(item.end_date)} · ${daysLabel(item.end_date)}` : 'Kein Enddatum' }}
            </v-chip>
          </div>
          <div class="text-body-2">{{ formatEur(item.praemie_eur) }} / {{ item.zahlungsintervall }}</div>
          <div v-if="getCancellationInfo(item)" class="text-body-2 mt-1">
            <v-icon size="small" :color="cancellationColor(item)">mdi-calendar-remove</v-icon>
            Kündbar bis {{ formatDate(getCancellationInfo(item).deadline) }}
            <span v-if="getCancellationInfo(item).wirksamZum" class="text-caption text-medium-emphasis">
              · endet dann {{ formatDate(getCancellationInfo(item).wirksamZum) }}
            </span>
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
      <template #item.kategorie="{ item }">
        <v-chip size="small" color="primary">{{ item.kategorie }}</v-chip>
      </template>
      <template #item.praemie_eur="{ item }">
        {{ formatEur(item.praemie_eur) }} / {{ item.zahlungsintervall }}
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

    <v-dialog v-model="dialog" max-width="600" :fullscreen="smAndDown">
      <v-card>
        <v-card-title class="d-flex align-center">
          {{ editing.id ? 'Versicherung bearbeiten' : 'Neue Versicherung' }}
          <v-spacer />
          <v-btn v-if="smAndDown" icon="mdi-close" variant="text" @click="dialog = false" />
        </v-card-title>
        <v-card-text>
          <p class="text-body-2 text-medium-emphasis mb-4">
            Pflichtfelder zuerst ausfüllen, damit der Vertrag eindeutig zugeordnet werden kann.
          </p>
          <v-form>
            <v-text-field v-model="editing.name" label="Name" required />
            <v-select v-model="editing.kategorie" :items="kategorien" label="Kategorie" required />
            <v-text-field v-model="editing.versicherer" label="Versicherer" required />
            <v-text-field v-model="editing.vertragsnummer" label="Vertragsnummer" required />
            <v-row>
              <v-col cols="12" sm="6"><v-text-field v-model="editing.start_date" label="Start" type="date" /></v-col>
              <v-col cols="12" sm="6"><v-text-field v-model="editing.end_date" label="Ende" type="date" /></v-col>
            </v-row>
            <v-row>
              <v-col cols="12" sm="6">
                <v-text-field
                  v-model.number="editing.praemie_eur"
                  label="Prämie pro Zahlung (€)"
                  type="number"
                  hint="Betrag je Zahlungsperiode, z.&thinsp;B. 50 bei monatlicher Zahlung"
                  persistent-hint
                />
              </v-col>
              <v-col cols="12" sm="6"><v-select v-model="editing.zahlungsintervall" :items="intervals" label="Intervall" /></v-col>
            </v-row>
            <v-row>
              <v-col cols="12" sm="6">
                <v-text-field
                  v-model="kuendigungBisInput"
                  label="Kündbar jeweils bis (TT.MM.) – optional"
                  placeholder="z. B. 30.09."
                  hint="Leer lassen, wenn unbekannt"
                  persistent-hint
                  clearable
                  :rules="[recurringDateRule]"
                />
              </v-col>
              <v-col cols="12" sm="6">
                <v-text-field
                  v-model="kuendigungZumInput"
                  label="Vertrag endet dann zum (TT.MM.) – optional"
                  placeholder="z. B. 31.12."
                  hint="Leer lassen, wenn unbekannt"
                  persistent-hint
                  clearable
                  :rules="[recurringDateRule]"
                />
              </v-col>
            </v-row>
            <v-textarea v-model="editing.notes" label="Notizen" rows="2" />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="dialog = false">Abbrechen</v-btn>
          <v-btn color="primary" :disabled="!canSave" @click="save">Speichern</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="recDialog" max-width="500">
      <v-card>
        <v-card-title>KI-Empfehlung</v-card-title>
        <v-card-text>
          <div v-if="recLoading" class="text-center py-6">
            <v-progress-circular indeterminate color="primary" class="mb-3" />
            <div class="text-body-2 text-medium-emphasis">KI analysiert Versicherung…</div>
          </div>
          <template v-else-if="rec">
            <v-chip :color="recColor" class="mb-3">{{ rec.handlungsbedarf }}</v-chip>
            <p><strong>{{ rec.hinweis }}</strong></p>
            <p class="mt-2">{{ rec.details }}</p>
          </template>
        </v-card-text>
        <v-card-actions>
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

    <v-snackbar v-model="snack.show" :color="snack.color">{{ snack.text }}</v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'
import { insurancesApi, documentsApi } from '../api'
import { insuranceCategories, paymentIntervals } from '../constants'
import {
  daysLabel,
  daysUntil,
  expiryColor,
  formatCurrency,
  formatDate,
  formatRecurringDate,
  getCancellationInfo,
  parseRecurringDate,
} from '../utils'

const route = useRoute()
const router = useRouter()
const { smAndDown } = useDisplay()
const items = ref([])
const dialog = ref(false)
const recDialog = ref(false)
const rec = ref(null)
const recLoading = ref(false)
const editing = ref({})
const snack = ref({ show: false, color: 'success', text: '' })
const search = ref('')
const statusFilter = ref('all')
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

// Eingabe der Kündigungsdaten als "TT.MM."-Strings (werden beim Speichern geparst)
const kuendigungBisInput = ref('')
const kuendigungZumInput = ref('')

const recurringDateRule = (v) =>
  parseRecurringDate(v) !== undefined || 'Format TT.MM., z. B. 30.09.'

function cancellationColor(item) {
  const info = getCancellationInfo(item)
  if (!info) return 'grey'
  const days = daysUntil(info.deadline)
  if (days <= 14) return 'error'
  if (days <= 60) return 'warning'
  return 'success'
}

const kategorien = insuranceCategories
const intervals = paymentIntervals

const pdfUrl = '/api/exports/insurances.pdf'
const xlsxUrl = '/api/exports/insurances.xlsx'

const recColor = computed(() => ({ keiner: 'success', pruefen: 'warning', handeln: 'error' })[rec.value?.handlungsbedarf?.toLowerCase?.()] || 'grey')
const formatEur = formatCurrency
const endColor = expiryColor
const filteredItems = computed(() => {
  const query = search.value.trim().toLowerCase()
  return items.value.filter((item) => {
    const matchesQuery = !query || [item.name, item.kategorie, item.versicherer, item.vertragsnummer]
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
const canSave = computed(() => Boolean(
  editing.value.name &&
  editing.value.kategorie &&
  editing.value.versicherer &&
  editing.value.vertragsnummer
))
async function load() {
  try {
    items.value = await insurancesApi.list()
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Laden fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  }
}

function openNew() {
  editing.value = { kategorie: 'Sonstige', zahlungsintervall: 'jährlich', notes: '' }
  kuendigungBisInput.value = ''
  kuendigungZumInput.value = ''
  dialog.value = true
}
function openEdit(item) {
  editing.value = { ...item }
  kuendigungBisInput.value = formatRecurringDate(item.kuendigung_bis_tag, item.kuendigung_bis_monat)
  kuendigungZumInput.value = formatRecurringDate(item.kuendigung_zum_tag, item.kuendigung_zum_monat)
  dialog.value = true
}
async function save() {
  try {
    const payload = { ...editing.value }
    delete payload.created_at
    // '' (geleertes Zahlenfeld) → null, sonst lehnt das Backend mit 422 ab
    if (payload.praemie_eur === '' || payload.praemie_eur == null) payload.praemie_eur = null
    if (payload.start_date === '') payload.start_date = null
    if (payload.end_date === '') payload.end_date = null

    // Kündigungsdaten aus den "TT.MM."-Eingaben übernehmen
    const bis = parseRecurringDate(kuendigungBisInput.value)
    const zum = parseRecurringDate(kuendigungZumInput.value)
    if (bis === undefined || zum === undefined) {
      snack.value = { show: true, color: 'error', text: 'Kündigungsdatum bitte als TT.MM. angeben, z. B. 30.09.' }
      return
    }
    payload.kuendigung_bis_tag = bis?.tag ?? null
    payload.kuendigung_bis_monat = bis?.monat ?? null
    payload.kuendigung_zum_tag = zum?.tag ?? null
    payload.kuendigung_zum_monat = zum?.monat ?? null

    if (editing.value.id) {
      await insurancesApi.update(editing.value.id, payload)
    } else {
      await insurancesApi.create(payload)
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
    await insurancesApi.delete(deleteTarget.value.id)
    await load()
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Löschen fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  } finally {
    deleteTarget.value = null
  }
}
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
  } finally {
    attaching.value = false
  }
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
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Löschen fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  } finally {
    docDeleteTarget.value = null
  }
}

async function getRecommendation(item) {
  rec.value = null
  recLoading.value = true
  recDialog.value = true
  try {
    rec.value = await documentsApi.recommendation(item.id)
  } catch (e) {
    recDialog.value = false
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
