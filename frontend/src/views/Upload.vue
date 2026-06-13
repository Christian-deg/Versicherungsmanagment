<template>
  <div>
    <div class="d-flex flex-column flex-md-row align-start align-md-center mb-4 ga-3">
      <div>
        <h1 class="text-h4">Dokument hochladen</h1>
        <p class="text-medium-emphasis mt-1">
          Lade eine Police oder eine Produktrechnung hoch — die KI erkennt automatisch, worum es sich handelt.
        </p>
      </div>
    </div>

    <v-alert type="info" variant="tonal" class="mb-4">
      <strong>Einfacher Ablauf:</strong> Datei auswählen → Typ wird erkannt (Versicherung oder Rechnung) →
      KI-Vorschlag prüfen → speichern.
    </v-alert>

    <v-card v-if="!preview">
      <v-card-text>
        <v-file-input
          v-model="files"
          label="PDF oder Foto (JPEG/PNG) — Police oder Rechnung"
          accept="application/pdf,image/png,image/jpeg"
          prepend-icon="mdi-camera"
          show-size
          multiple
          hint="Versicherungsdokumente bis 80 MB, Rechnungen bis 10 MB. Mehrere Dateien möglich – die erste wird von der KI analysiert."
          persistent-hint
          :disabled="loading"
        />
        <v-btn
          color="primary"
          :loading="loading"
          :disabled="!primaryFile || loading"
          :block="smAndDown"
          @click="onUpload"
          prepend-icon="mdi-cloud-upload"
          class="mt-3"
        >
          {{ uploadLabel }}
        </v-btn>
        <v-progress-linear v-if="loading" indeterminate color="primary" class="mt-3" />

        <v-alert v-if="typeChoice" type="info" variant="tonal" class="mt-3">
          Der Dokumenttyp konnte nicht eindeutig erkannt werden. Wie soll die Datei verarbeitet werden?
          <div class="d-flex flex-wrap ga-2 mt-2">
            <v-btn size="small" color="primary" @click="analyzeAsInsurance">Als Versicherung analysieren</v-btn>
            <v-btn size="small" variant="outlined" @click="goToInvoiceFlow">Als Rechnung verarbeiten</v-btn>
          </div>
        </v-alert>

        <p class="mt-3 text-medium-emphasis">
          Versicherungen: KI extrahiert Versicherer, Vertragsnummer, Laufzeit und Prämie; weitere
          Dateien werden als zusätzliche Dokumente gespeichert. Rechnungen: Weiterleitung in den
          Rechnungs-Ablauf mit Kaufdatum-/Betrags-Erkennung.
        </p>
      </v-card-text>
    </v-card>

    <v-card v-else>
      <v-card-title>
        Extraktionsvorschau
        <v-chip class="ml-2" :color="confColor">Konfidenz: {{ preview.konfidenz }}</v-chip>
        <v-chip v-if="extraDocumentIds.length" class="ml-2" color="info" variant="tonal">
          + {{ extraDocumentIds.length }} weiteres Dokument{{ extraDocumentIds.length > 1 ? 'e' : '' }}
        </v-chip>
      </v-card-title>
      <v-card-text>
        <v-alert v-if="preview.hinweise" type="info" variant="tonal" class="mb-3">{{ preview.hinweise }}</v-alert>
        <v-row class="mb-1">
          <v-col cols="12" md="4">
            <v-chip color="primary" variant="tonal" size="small">Kategorie: {{ preview.kategorie || '–' }}</v-chip>
          </v-col>
          <v-col cols="12" md="4">
            <v-chip color="secondary" variant="tonal" size="small">Versicherer: {{ preview.versicherer || '–' }}</v-chip>
          </v-col>
        </v-row>
        <p class="text-body-2 text-medium-emphasis mb-3">
          Prüfe besonders Name, Vertragsnummer und Laufzeit. Alle Felder sind editierbar.
        </p>
        <v-row>
          <v-col cols="12" md="6"><v-text-field v-model="preview.versicherer" label="Versicherer" @update:model-value="syncName" /></v-col>
          <v-col cols="12" md="6"><v-select v-model="preview.kategorie" :items="kategorien" label="Kategorie" @update:model-value="syncName" /></v-col>
          <v-col cols="12" md="6"><v-text-field v-model="form.name" label="Name (frei wählbar)" @update:model-value="nameManuallyEdited = true" /></v-col>
          <v-col cols="12" md="6"><v-text-field v-model="preview.vertragsnummer" label="Vertragsnummer" /></v-col>
          <v-col cols="12" sm="6"><v-text-field v-model="preview.start_date" label="Start" type="date" /></v-col>
          <v-col cols="12" sm="6"><v-text-field v-model="preview.end_date" label="Ende" type="date" /></v-col>
          <v-col cols="12" sm="6">
            <v-text-field
              v-model.number="preview.praemie_eur"
              label="Prämie pro Zahlung (€)"
              type="number"
              hint="Betrag je Zahlungsperiode, z.&thinsp;B. 50 bei monatlicher Zahlung"
              persistent-hint
            />
          </v-col>
          <v-col cols="12" sm="6"><v-select v-model="preview.zahlungsintervall" :items="intervals" label="Intervall" /></v-col>
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
      </v-card-text>
      <v-card-actions class="flex-wrap ga-2">
        <v-btn @click="reset">Verwerfen</v-btn>
        <v-spacer />
        <div class="text-right">
          <v-btn color="primary" :loading="saving" :disabled="!canConfirm" @click="onConfirm">Bestätigen & speichern</v-btn>
          <div v-if="!canConfirm" class="text-caption text-error mt-1">
            Bitte mindestens Kategorie, Versicherer und Vertragsnummer ergänzen.
          </div>
        </div>
      </v-card-actions>
    </v-card>

    <v-snackbar v-model="snack.show" :color="snack.color">{{ snack.text }}</v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'
import { documentsApi } from '../api'
import { insuranceCategories, paymentIntervals } from '../constants'
import { useTransferStore } from '../stores/transfer'
import { confidenceColor, formatRecurringDate, parseRecurringDate } from '../utils'

const { smAndDown } = useDisplay()
const router = useRouter()
const transfer = useTransferStore()
const files = ref([])
const preview = ref(null)
const form = ref({ name: '' })
const loading = ref(false)
const loadingPhase = ref('')  // 'uploading' | 'analyzing'
const saving = ref(false)
const nameManuallyEdited = ref(false)
const extraDocumentIds = ref([])
const kuendigungBisInput = ref('')
const kuendigungZumInput = ref('')

const recurringDateRule = (v) =>
  parseRecurringDate(v) !== undefined || 'Format TT.MM., z. B. 30.09.'
const snack = ref({ show: false, color: 'success', text: '' })

const kategorien = insuranceCategories
const intervals = paymentIntervals

// Erste Datei (für KI-Analyse), oder null wenn keine ausgewählt
const primaryFile = computed(() => {
  const f = files.value
  if (!f) return null
  return Array.isArray(f) ? (f[0] ?? null) : f
})

const typeChoice = ref(false)

const uploadLabel = computed(() => {
  if (!loading.value) return 'Hochladen & analysieren'
  if (loadingPhase.value === 'classifying') return 'Dokumenttyp wird erkannt…'
  if (loadingPhase.value === 'analyzing') return 'KI analysiert Dokument…'
  if (loadingPhase.value === 'extra') return 'Weitere Dokumente hochladen…'
  return 'Hochladen…'
})

const confColor = computed(() => confidenceColor(preview.value?.konfidenz))
const canConfirm = computed(() =>
  Boolean(
    preview.value?.kategorie &&
    preview.value?.versicherer &&
    preview.value?.vertragsnummer &&
    form.value.name
  )
)

function syncName() {
  if (!nameManuallyEdited.value) {
    form.value.name = defaultPolicyName()
  }
}

async function onUpload() {
  loading.value = true
  loadingPhase.value = 'classifying'
  typeChoice.value = false
  try {
    const cls = await documentsApi.classify(primaryFile.value)
    if (cls.typ === 'rechnung') {
      goToInvoiceFlow()
      return
    }
    if (cls.typ === 'unbekannt') {
      typeChoice.value = true
      return
    }
  } catch (e) {
    // Klassifizierung ist nur Komfort — bei Fehlern Auswahl anbieten
    typeChoice.value = true
    return
  } finally {
    loading.value = false
    loadingPhase.value = ''
  }
  await analyzeAsInsurance()
}

function goToInvoiceFlow() {
  const allFiles = (Array.isArray(files.value) ? files.value : [files.value]).filter(Boolean)
  if (allFiles.length > 1) {
    snack.value = {
      show: true,
      color: 'info',
      text: 'Rechnung erkannt — nur die erste Datei wird in den Rechnungs-Ablauf übernommen.',
    }
  }
  transfer.setPendingInvoiceFile(primaryFile.value)
  router.push({ path: '/invoices', query: { upload: '1' } })
}

async function analyzeAsInsurance() {
  loading.value = true
  loadingPhase.value = 'analyzing'
  typeChoice.value = false
  nameManuallyEdited.value = false
  extraDocumentIds.value = []
  try {
    const primary = primaryFile.value
    preview.value = await documentsApi.upload(primary)
    form.value.name = defaultPolicyName()
    kuendigungBisInput.value = formatRecurringDate(
      preview.value.kuendigung_bis_tag, preview.value.kuendigung_bis_monat
    )
    kuendigungZumInput.value = formatRecurringDate(
      preview.value.kuendigung_zum_tag, preview.value.kuendigung_zum_monat
    )

    // Weitere Dateien ohne KI-Analyse hochladen
    const allFiles = Array.isArray(files.value) ? files.value : [files.value]
    const remaining = allFiles.slice(1).filter(Boolean)
    if (remaining.length) {
      loadingPhase.value = 'extra'
      const results = await Promise.allSettled(remaining.map(f => documentsApi.uploadExtra(f)))
      const failed = results.filter(r => r.status === 'rejected')
      for (const r of results) {
        if (r.status === 'fulfilled') {
          extraDocumentIds.value.push(r.value.id)
        }
      }
      if (failed.length) {
        const msg = failed.length === 1
          ? 'Ein Zusatzdokument konnte nicht hochgeladen werden.'
          : `${failed.length} Zusatzdokumente konnten nicht hochgeladen werden.`
        snack.value = { show: true, color: 'warning', text: msg }
      }
    }
  } catch (e) {
    snack.value = { show: true, color: 'error', text: e.response?.data?.detail || 'Fehler beim Upload' }
  } finally {
    loading.value = false
    loadingPhase.value = ''
  }
}

async function onConfirm() {
  saving.value = true
  try {
    const name = form.value.name || defaultPolicyName()
    if (!name) {
      throw new Error('Bitte gib einen Namen für die Versicherung an.')
    }
    const bis = parseRecurringDate(kuendigungBisInput.value)
    const zum = parseRecurringDate(kuendigungZumInput.value)
    if (bis === undefined || zum === undefined) {
      throw new Error('Kündigungsdatum bitte als TT.MM. angeben, z. B. 30.09.')
    }
    const payload = {
      name,
      kategorie: preview.value.kategorie,
      versicherer: preview.value.versicherer,
      vertragsnummer: preview.value.vertragsnummer,
      start_date: preview.value.start_date || null,
      end_date: preview.value.end_date || null,
      // '' (geleertes Zahlenfeld) → null; 0 bleibt erhalten
      praemie_eur: preview.value.praemie_eur === '' || preview.value.praemie_eur == null
        ? null
        : preview.value.praemie_eur,
      zahlungsintervall: preview.value.zahlungsintervall,
      kuendigung_bis_tag: bis?.tag ?? null,
      kuendigung_bis_monat: bis?.monat ?? null,
      kuendigung_zum_tag: zum?.tag ?? null,
      kuendigung_zum_monat: zum?.monat ?? null,
      notes: preview.value.hinweise,
      extra_document_ids: extraDocumentIds.value,
    }
    await documentsApi.confirm(preview.value.document_id, payload)
    await router.push({ path: '/insurances', query: { saved: '1' } })
  } catch (e) {
    snack.value = { show: true, color: 'error', text: e.response?.data?.detail || e.message || 'Fehler beim Speichern' }
  } finally {
    saving.value = false
  }
}

function reset() {
  preview.value = null
  files.value = []
  extraDocumentIds.value = []
  nameManuallyEdited.value = false
  kuendigungBisInput.value = ''
  kuendigungZumInput.value = ''
}

function defaultPolicyName() {
  if (!preview.value?.kategorie || !preview.value?.versicherer) return ''
  return `${preview.value.kategorie} – ${preview.value.versicherer}`.trim()
}
</script>
