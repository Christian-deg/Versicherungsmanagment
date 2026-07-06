<template>
  <div>
    <v-skeleton-loader v-if="loading" type="article" />

    <template v-else-if="item">
      <div class="d-flex flex-column flex-md-row align-start align-md-center mb-4 ga-3">
        <div>
          <div class="d-flex align-center ga-2 flex-wrap">
            <v-btn icon="mdi-arrow-left" variant="text" aria-label="Zurück zur Liste" to="/insurances" />
            <h1 class="text-h4">{{ item.name }}</h1>
          </div>
          <p class="text-medium-emphasis mt-1 ml-md-12">
            {{ item.versicherer }} · Nr. {{ item.vertragsnummer }}
          </p>
        </div>
        <v-spacer />
        <div class="d-flex flex-wrap ga-2">
          <v-btn
            variant="outlined"
            prepend-icon="mdi-robot"
            :to="{ path: '/chat', query: { context: item.name } }"
          >
            Frage zum Vertrag
          </v-btn>
          <v-btn variant="outlined" prepend-icon="mdi-pencil" @click="editDialog = true">Bearbeiten</v-btn>
          <v-btn variant="outlined" color="error" prepend-icon="mdi-delete" @click="deleteDialog = true">Löschen</v-btn>
        </div>
      </div>

      <v-alert v-if="issues.length" type="warning" variant="tonal" class="mb-4">
        <div v-for="issue in issues" :key="issue">• {{ issue }}</div>
      </v-alert>

      <v-row>
        <!-- Stammdaten + Fristen -->
        <v-col cols="12" md="6">
          <v-card height="100%">
            <v-card-title>
              <v-icon :icon="categoryIcon(item.kategorie)" class="mr-2" />Stammdaten
            </v-card-title>
            <v-card-text>
              <v-list density="compact">
                <v-list-item title="Kategorie">
                  <template #append>
                    <v-chip size="small" color="primary" :prepend-icon="categoryIcon(item.kategorie)">
                      {{ item.kategorie }}
                    </v-chip>
                  </template>
                </v-list-item>
                <v-list-item v-if="item.person" title="Gehört zu">
                  <template #append>
                    <v-chip size="small" variant="tonal" prepend-icon="mdi-account">{{ item.person }}</v-chip>
                  </template>
                </v-list-item>
                <v-list-item title="Prämie">
                  <template #append>
                    <div class="text-right">
                      <div>{{ formatCurrency(item.praemie_eur) }} / {{ item.zahlungsintervall }}</div>
                      <div v-if="yearly" class="text-caption text-medium-emphasis">
                        {{ formatCurrency(yearly) }} pro Jahr
                      </div>
                    </div>
                  </template>
                </v-list-item>
                <v-list-item title="Laufzeit">
                  <template #append>
                    {{ item.start_date ? formatDate(item.start_date) : '–' }} bis
                    {{ item.end_date ? formatDate(item.end_date) : 'unbefristet' }}
                  </template>
                </v-list-item>
                <v-list-item v-if="item.end_date" title="Restlaufzeit">
                  <template #append>
                    <v-chip size="small" :color="expiryColor(item.end_date)">{{ daysLabel(item.end_date) }}</v-chip>
                  </template>
                </v-list-item>
                <v-list-item title="Kündigungsfrist">
                  <template #append>
                    <template v-if="cancellation">
                      <div class="text-right">
                        <v-chip size="small" :color="expiryColor(cancellation.deadline)">
                          bis {{ formatDate(cancellation.deadline) }}
                        </v-chip>
                        <div v-if="cancellation.wirksamZum" class="text-caption text-medium-emphasis mt-1">
                          endet dann {{ formatDate(cancellation.wirksamZum) }}
                        </div>
                      </div>
                    </template>
                    <span v-else class="text-medium-emphasis">nicht hinterlegt</span>
                  </template>
                </v-list-item>
              </v-list>
              <div v-if="item.notes" class="mt-2">
                <div class="text-subtitle-2 mb-1">Notizen</div>
                <p class="text-body-2" style="white-space: pre-wrap">{{ item.notes }}</p>
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Prämienverlauf -->
        <v-col cols="12" md="6">
          <v-card height="100%">
            <v-card-title class="d-flex align-center">
              <v-icon icon="mdi-chart-line" class="mr-2" />Prämienverlauf
              <v-spacer />
              <v-chip
                v-if="trend"
                size="small"
                :color="trend.pct > 0 ? 'error' : 'success'"
                variant="tonal"
                :prepend-icon="trend.pct > 0 ? 'mdi-trending-up' : 'mdi-trending-down'"
              >
                {{ trend.pct > 0 ? '+' : '' }}{{ trend.pct }} % seit {{ trend.sinceYear }}
              </v-chip>
            </v-card-title>
            <v-card-text>
              <v-timeline v-if="history.length > 1" density="compact" side="end">
                <v-timeline-item
                  v-for="(h, idx) in [...history].reverse()"
                  :key="idx"
                  :dot-color="idx === 0 ? 'primary' : 'grey'"
                  size="x-small"
                >
                  <div class="d-flex justify-space-between ga-4">
                    <span>{{ formatCurrency(h.praemie_eur) }} / {{ h.zahlungsintervall }}</span>
                    <span class="text-medium-emphasis">{{ formatDate(h.changed_at) }}</span>
                  </div>
                </v-timeline-item>
              </v-timeline>
              <p v-else class="text-medium-emphasis mb-0">
                Noch keine Prämienänderungen erfasst. Sobald du die Prämie beim Bearbeiten änderst
                (z.&thinsp;B. nach einer Beitragserhöhung), entsteht hier der Verlauf.
              </p>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Dokumente -->
        <v-col cols="12" md="6">
          <v-card height="100%">
            <v-card-title><v-icon icon="mdi-paperclip" class="mr-2" />Dokumente</v-card-title>
            <v-card-text>
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
                <v-btn color="primary" :loading="attaching" :disabled="!hasNewDocFiles || attaching" @click="attachDocs">
                  Hinzufügen
                </v-btn>
              </div>
              <v-list v-if="docs.length" lines="two" density="compact">
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
                    <v-btn icon="mdi-delete" size="small" variant="text" color="error" @click="deleteDoc(d)" />
                  </template>
                </v-list-item>
              </v-list>
              <p v-else class="text-medium-emphasis mb-0">
                Noch keine Dokumente — füge die Police hinzu, damit der Assistent sie durchsuchen kann.
              </p>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Empfehlung -->
        <v-col cols="12" md="6">
          <v-card height="100%">
            <v-card-title class="d-flex align-center">
              <v-icon icon="mdi-lightbulb" class="mr-2" />KI-Empfehlung
              <v-spacer />
              <v-btn variant="text" prepend-icon="mdi-refresh" :loading="recLoading" @click="regenerate">
                Neu bewerten
              </v-btn>
            </v-card-title>
            <v-card-text>
              <template v-if="rec">
                <v-chip :color="recColor" class="mb-3">{{ rec.handlungsbedarf }}</v-chip>
                <p><strong>{{ rec.hinweis }}</strong></p>
                <p class="mt-2">{{ rec.details }}</p>
                <div class="text-caption text-medium-emphasis mt-3">
                  Stand: {{ formatDate(rec.created_at) }} · wird jährlich automatisch erneuert
                </div>
              </template>
              <p v-else-if="recLoading" class="text-medium-emphasis mb-0">KI bewertet Versicherung…</p>
              <p v-else class="text-medium-emphasis mb-0">
                Noch keine Empfehlung — mit „Neu bewerten" erzeugst du die erste Einschätzung.
              </p>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <InsuranceFormDialog v-model="editDialog" :insurance="item" @saved="onSaved" />

      <v-dialog v-model="deleteDialog" max-width="400">
        <v-card>
          <v-card-title>Versicherung löschen</v-card-title>
          <v-card-text>
            Möchtest du die Versicherung <strong>„{{ item.name }}"</strong> wirklich löschen?
            <v-alert type="warning" variant="tonal" density="compact" class="mt-3">
              Alle zugehörigen Dokumente und KI-Daten werden ebenfalls gelöscht. Diese Aktion
              kann nicht rückgängig gemacht werden.
            </v-alert>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn @click="deleteDialog = false">Abbrechen</v-btn>
            <v-btn color="error" @click="onDelete">Löschen</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </template>

    <v-empty-state
      v-else
      headline="Versicherung nicht gefunden"
      text="Der Vertrag existiert nicht (mehr)."
      icon="mdi-shield-off-outline"
    >
      <template #actions>
        <v-btn color="primary" to="/insurances">Zur Vertragsliste</v-btn>
      </template>
    </v-empty-state>

    <v-snackbar v-model="snack.show" :color="snack.color">{{ snack.text }}</v-snackbar>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { documentsApi, insurancesApi } from '../api'
import InsuranceFormDialog from '../components/InsuranceFormDialog.vue'
import { categoryIcon } from '../constants'
import {
  daysLabel,
  expiryColor,
  formatCurrency,
  formatDate,
  getCancellationInfo,
  premiumTrend,
  qualityIssues,
  yearlyPremium,
} from '../utils'

const route = useRoute()
const router = useRouter()

const item = ref(null)
const docs = ref([])
const history = ref([])
const rec = ref(null)
const loading = ref(true)
const recLoading = ref(false)
const editDialog = ref(false)
const deleteDialog = ref(false)
const newDocFiles = ref([])
const attaching = ref(false)
const snack = ref({ show: false, color: 'success', text: '' })

const insuranceId = Number(route.params.id)

const yearly = computed(() => yearlyPremium(item.value))
const cancellation = computed(() => (item.value ? getCancellationInfo(item.value) : null))
const trend = computed(() => premiumTrend(history.value))
const issues = computed(() => (item.value ? qualityIssues(item.value, docs.value.length > 0) : []))
const recColor = computed(
  () => ({ keiner: 'success', pruefen: 'warning', handeln: 'error' })[rec.value?.handlungsbedarf?.toLowerCase?.()] || 'grey'
)
const hasNewDocFiles = computed(() => {
  const f = newDocFiles.value
  return Array.isArray(f) ? f.length > 0 : Boolean(f)
})

async function load() {
  loading.value = true
  try {
    const [ins, documents, allHistory, recommendation] = await Promise.all([
      insurancesApi.get(insuranceId),
      documentsApi.list(insuranceId),
      insurancesApi.premiumHistory(),
      documentsApi.recommendationGet(insuranceId).catch(() => null),
    ])
    item.value = ins
    docs.value = documents
    history.value = allHistory.filter((h) => h.insurance_id === insuranceId)
    rec.value = recommendation
  } catch (e) {
    if (e.response?.status !== 404) {
      snack.value = { show: true, color: 'error', text: 'Laden fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
    }
    item.value = null
  } finally {
    loading.value = false
  }
}

async function onSaved() {
  snack.value = { show: true, color: 'success', text: 'Versicherung gespeichert' }
  await load()
}

async function onDelete() {
  deleteDialog.value = false
  try {
    await insurancesApi.delete(insuranceId)
    await router.push('/insurances')
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Löschen fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  }
}

async function attachDocs() {
  const f = newDocFiles.value
  const list = (Array.isArray(f) ? f : [f]).filter(Boolean)
  if (!list.length) return
  attaching.value = true
  try {
    const results = await Promise.allSettled(list.map((file) => documentsApi.attach(insuranceId, file)))
    const failed = results.filter((r) => r.status === 'rejected')
    snack.value = failed.length
      ? { show: true, color: 'warning', text: `${failed.length} von ${list.length} Dokument(en) fehlgeschlagen.` }
      : { show: true, color: 'success', text: list.length === 1 ? 'Dokument hinzugefügt.' : `${list.length} Dokumente hinzugefügt.` }
    newDocFiles.value = []
    docs.value = await documentsApi.list(insuranceId)
  } finally {
    attaching.value = false
  }
}

async function deleteDoc(d) {
  try {
    await documentsApi.delete(d.id)
    docs.value = await documentsApi.list(insuranceId)
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Löschen fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  }
}

async function regenerate() {
  recLoading.value = true
  try {
    rec.value = await documentsApi.recommendation(insuranceId)
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Empfehlung fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  } finally {
    recLoading.value = false
  }
}

onMounted(load)
</script>
