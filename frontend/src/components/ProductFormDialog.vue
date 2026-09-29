<template>
  <v-dialog :model-value="modelValue" max-width="600" :fullscreen="smAndDown" @update:model-value="close">
    <v-card>
      <v-card-title class="d-flex align-center">
        {{ editing.id ? 'Produkt bearbeiten' : 'Neues Produkt' }}
        <v-spacer />
        <v-btn v-if="smAndDown" icon="mdi-close" variant="text" @click="close(false)" />
      </v-card-title>
      <v-card-text>
        <p class="text-body-2 text-medium-emphasis mb-4">
          Ein Garantieende hilft dir, rechtzeitig vor Ablauf erinnert zu werden.
        </p>
        <v-text-field v-model="editing.name" label="Name" required />
        <v-row>
          <v-col cols="12" sm="6"><ProductCategoryField v-model="editing.kategorie" /></v-col>
          <v-col cols="12" sm="6">
            <v-text-field
              v-model="editing.seriennummer"
              label="Seriennummer – optional"
              hint="Wird im Garantiefall oft abgefragt"
              persistent-hint
            />
          </v-col>
        </v-row>
        <v-row>
          <v-col cols="12" sm="6">
            <v-text-field
              v-model="editing.purchase_date"
              label="Kaufdatum"
              type="date"
              @update:model-value="onPurchaseDateInput"
            />
          </v-col>
          <v-col cols="12" sm="6"><v-text-field v-model="editing.warranty_end" label="Garantieende" type="date" /></v-col>
        </v-row>
        <v-select
          v-model="editing.linked_insurance_id"
          :items="insuranceOptions"
          label="Verknüpfte Versicherung (optional)"
          clearable
        />
        <v-textarea v-model="editing.notes" label="Notizen" rows="2" />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="close(false)">Abbrechen</v-btn>
        <v-btn color="primary" :disabled="!editing.name" :loading="saving" @click="save">Speichern</v-btn>
      </v-card-actions>
    </v-card>

    <v-snackbar v-model="snack.show" :color="snack.color">{{ snack.text }}</v-snackbar>
  </v-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useDisplay } from 'vuetify'
import { insurancesApi, productsApi } from '../api'
import { parseDateValue, toIsoDate } from '../utils'
import ProductCategoryField from './ProductCategoryField.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  // Zu bearbeitendes Produkt; null/leer = Neuanlage
  product: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'saved'])

const { smAndDown } = useDisplay()
const editing = ref({})
const insurances = ref([])
const saving = ref(false)
const snack = ref({ show: false, color: 'error', text: '' })

const insuranceOptions = computed(() =>
  insurances.value.map((i) => ({ title: `${i.name} (${i.versicherer})`, value: i.id }))
)

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    editing.value = props.product
      ? { ...props.product }
      : { name: '', kategorie: '', seriennummer: '', notes: '', linked_insurance_id: null }
    try {
      insurances.value = await insurancesApi.list()
    } catch {
      insurances.value = []
    }
  }
)

// Kaufdatum vom Nutzer geändert → Garantieende auf +2 Jahre setzen (nur wenn noch leer).
// Bewusst kein watch: der feuerte schon beim Öffnen eines Produkts ohne Garantieende
// und hat beim Speichern ungefragt ein Garantieende eingetragen.
function onPurchaseDateInput(newDate) {
  if (!newDate || editing.value.warranty_end) return
  const d = parseDateValue(newDate)
  d.setFullYear(d.getFullYear() + 2)
  editing.value.warranty_end = toIsoDate(d)
}

function close(value) {
  emit('update:modelValue', Boolean(value))
}

async function save() {
  saving.value = true
  try {
    const payload = { ...editing.value }
    delete payload.created_at
    delete payload.id
    // '' (geleertes Datumsfeld) → null, sonst lehnt das Backend mit 422 ab
    if (payload.purchase_date === '') payload.purchase_date = null
    if (payload.warranty_end === '') payload.warranty_end = null
    if (payload.seriennummer === '') payload.seriennummer = null
    if (!payload.kategorie?.trim()) payload.kategorie = 'Sonstiges'

    const saved = editing.value.id
      ? await productsApi.update(editing.value.id, payload)
      : await productsApi.create(payload)
    emit('saved', saved)
    emit('update:modelValue', false)
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Speichern fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  } finally {
    saving.value = false
  }
}
</script>
