<template>
  <v-dialog :model-value="modelValue" max-width="480" @update:model-value="close">
    <v-card>
      <v-card-title>Rechnung bearbeiten</v-card-title>
      <v-card-subtitle class="text-wrap">{{ invoice?.original_filename }}</v-card-subtitle>
      <v-card-text>
        <v-row>
          <v-col cols="12" sm="6">
            <v-text-field v-model="form.purchase_date" label="Kaufdatum" type="date" />
          </v-col>
          <v-col cols="12" sm="6">
            <v-text-field v-model="form.amount_eur" label="Betrag (€)" type="number" min="0" step="0.01" />
          </v-col>
        </v-row>
        <v-textarea v-model="form.notes" label="Notizen (Händler / Produkt)" rows="2" />
        <p class="text-caption text-medium-emphasis mb-0">
          Ein geändertes Kaufdatum berechnet die Aufbewahrungsfrist neu.
        </p>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="close(false)">Abbrechen</v-btn>
        <v-btn color="primary" :loading="saving" @click="save">Speichern</v-btn>
      </v-card-actions>
    </v-card>

    <v-snackbar v-model="snack.show" color="error">{{ snack.text }}</v-snackbar>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { invoicesApi } from '../api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  invoice: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'saved'])

const form = ref({ purchase_date: '', amount_eur: '', notes: '' })
const saving = ref(false)
const snack = ref({ show: false, text: '' })

watch(
  () => props.modelValue,
  (open) => {
    if (!open || !props.invoice) return
    form.value = {
      purchase_date: props.invoice.purchase_date || '',
      amount_eur: props.invoice.amount_eur ?? '',
      notes: props.invoice.notes || '',
    }
  }
)

function close(value) {
  emit('update:modelValue', Boolean(value))
}

async function save() {
  // Leere Felder → null (leert den Wert); Komma als Dezimaltrenner zulassen
  const rawAmount = String(form.value.amount_eur ?? '').trim().replace(',', '.')
  const amount = rawAmount === '' ? null : Number(rawAmount)
  if (amount !== null && (Number.isNaN(amount) || amount < 0)) {
    snack.value = { show: true, text: 'Bitte einen gültigen Betrag eingeben.' }
    return
  }
  saving.value = true
  try {
    const saved = await invoicesApi.update(props.invoice.id, {
      purchase_date: form.value.purchase_date || null,
      amount_eur: amount,
      notes: form.value.notes.trim() || null,
    })
    emit('saved', saved)
    close(false)
  } catch (e) {
    snack.value = { show: true, text: 'Speichern fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  } finally {
    saving.value = false
  }
}
</script>
