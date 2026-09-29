<template>
  <v-dialog :model-value="modelValue" max-width="600" :fullscreen="smAndDown" @update:model-value="close">
    <v-card>
      <v-card-title class="d-flex align-center">
        {{ editing.id ? 'Versicherung bearbeiten' : 'Neue Versicherung' }}
        <v-spacer />
        <v-btn v-if="smAndDown" icon="mdi-close" variant="text" @click="close(false)" />
      </v-card-title>
      <v-card-text>
        <p class="text-body-2 text-medium-emphasis mb-4">
          Pflichtfelder zuerst ausfüllen, damit der Vertrag eindeutig zugeordnet werden kann.
        </p>
        <v-form>
          <v-text-field v-model="editing.name" label="Name" required />
          <v-row>
            <v-col cols="12" sm="6">
              <v-select v-model="editing.kategorie" :items="kategorien" label="Kategorie" required />
            </v-col>
            <v-col cols="12" sm="6">
              <v-combobox
                v-model="editing.person"
                :items="personSuggestions"
                label="Gehört zu – optional"
                hint="z. B. Anna — für die Familien-Übersicht"
                persistent-hint
                clearable
              />
            </v-col>
          </v-row>
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
        <v-btn @click="close(false)">Abbrechen</v-btn>
        <v-btn color="primary" :disabled="!canSave" :loading="saving" @click="save">Speichern</v-btn>
      </v-card-actions>
    </v-card>

    <v-snackbar v-model="snack.show" :color="snack.color">{{ snack.text }}</v-snackbar>
  </v-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useDisplay } from 'vuetify'
import { insurancesApi } from '../api'
import { insuranceCategories, paymentIntervals } from '../constants'
import { formatRecurringDate, parseRecurringDate } from '../utils'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  // Zu bearbeitender Vertrag; null/leer = Neuanlage
  insurance: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'saved'])

const { smAndDown } = useDisplay()
const kategorien = insuranceCategories
const intervals = paymentIntervals

const editing = ref({})
const kuendigungBisInput = ref('')
const kuendigungZumInput = ref('')
const saving = ref(false)
const snack = ref({ show: false, color: 'error', text: '' })
// Bereits verwendete Personen-Labels als Vorschläge (Combobox erlaubt auch neue)
const personSuggestions = ref([])

const recurringDateRule = (v) =>
  parseRecurringDate(v) !== undefined || 'Format TT.MM., z. B. 30.09.'

// Beim Öffnen die Werte des übergebenen Vertrags übernehmen (bzw. Defaults für Neuanlage)
watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    if (props.insurance) {
      editing.value = { ...props.insurance }
      kuendigungBisInput.value = formatRecurringDate(
        props.insurance.kuendigung_bis_tag, props.insurance.kuendigung_bis_monat
      )
      kuendigungZumInput.value = formatRecurringDate(
        props.insurance.kuendigung_zum_tag, props.insurance.kuendigung_zum_monat
      )
    } else {
      editing.value = { kategorie: 'Sonstige', zahlungsintervall: 'jährlich', notes: '', person: null }
      kuendigungBisInput.value = ''
      kuendigungZumInput.value = ''
    }
    insurancesApi
      .list()
      .then((all) => {
        personSuggestions.value = [...new Set(all.map((i) => i.person).filter(Boolean))].sort()
      })
      .catch(() => {
        personSuggestions.value = []
      })
  }
)

const canSave = computed(() => Boolean(
  editing.value.name &&
  editing.value.kategorie &&
  editing.value.versicherer &&
  editing.value.vertragsnummer
))

function close(value) {
  emit('update:modelValue', Boolean(value))
}

async function save() {
  saving.value = true
  try {
    const payload = { ...editing.value }
    delete payload.created_at
    delete payload.id
    // '' (geleertes Zahlenfeld) → null, sonst lehnt das Backend mit 422 ab
    if (payload.praemie_eur === '' || payload.praemie_eur == null) payload.praemie_eur = null
    if (payload.start_date === '') payload.start_date = null
    if (payload.end_date === '') payload.end_date = null
    if (typeof payload.person === 'string') payload.person = payload.person.trim() || null

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

    const saved = editing.value.id
      ? await insurancesApi.update(editing.value.id, payload)
      : await insurancesApi.create(payload)
    emit('saved', saved)
    emit('update:modelValue', false)
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Speichern fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  } finally {
    saving.value = false
  }
}
</script>
