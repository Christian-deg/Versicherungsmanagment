<template>
  <div>
    <div class="d-flex flex-column flex-md-row align-start align-md-center mb-4 ga-3">
      <div>
        <h1 class="text-h4">Erinnerungen</h1>
        <p class="text-medium-emphasis mt-1">
          Verlauf aller Frist-Warnungen — und ein Test-Knopf, um die Pushover-Zustellung zu prüfen.
        </p>
      </div>
      <v-spacer />
      <v-btn
        color="primary"
        prepend-icon="mdi-bell-check"
        :loading="testing"
        @click="sendTest"
      >
        Test-Push senden
      </v-btn>
    </div>

    <v-alert type="info" variant="tonal" class="mb-4">
      Warnungen werden täglich um 8:00 Uhr geprüft: 90/30/7 Tage vor Vertragsablauf bzw.
      Garantieende und 30/7 Tage vor jeder Kündigungsfrist. Fehlgeschlagene Sendungen werden
      bis zu 3 Tage lang erneut versucht.
    </v-alert>

    <v-skeleton-loader v-if="loading" type="list-item-two-line" />

    <v-card v-else-if="items.length">
      <v-list lines="two">
        <v-list-item v-for="n in items" :key="n.id">
          <template #prepend>
            <v-avatar :color="statusColor(n.status)" variant="tonal">
              <v-icon :icon="typeIcon(n.ref_type)" />
            </v-avatar>
          </template>
          <v-list-item-title class="text-wrap">{{ n.message }}</v-list-item-title>
          <v-list-item-subtitle>
            Fällig am {{ formatDate(n.trigger_date) }} · Stufe: {{ n.days_before }} Tage vorher
            <template v-if="n.sent_at"> · gesendet am {{ formatDate(n.sent_at) }}</template>
            <template v-if="n.status === 'failed' && n.error"> · {{ n.error }}</template>
          </v-list-item-subtitle>
          <template #append>
            <v-chip :color="statusColor(n.status)" size="small">{{ statusLabel(n.status) }}</v-chip>
          </template>
        </v-list-item>
      </v-list>
    </v-card>

    <v-empty-state
      v-else
      headline="Noch keine Erinnerungen"
      text="Sobald ein Vertrag, eine Garantie oder eine Kündigungsfrist in den Warnzeitraum kommt, erscheint die Warnung hier."
      icon="mdi-bell-outline"
    />

    <v-snackbar v-model="snack.show" :color="snack.color" timeout="6000">{{ snack.text }}</v-snackbar>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { notificationsApi } from '../api'
import { formatDate } from '../utils'

const items = ref([])
const loading = ref(true)
const testing = ref(false)
const snack = ref({ show: false, color: 'success', text: '' })

const statusColor = (s) => ({ sent: 'success', pending: 'warning', failed: 'error' })[s] || 'grey'
const statusLabel = (s) => ({ sent: 'gesendet', pending: 'ausstehend', failed: 'fehlgeschlagen' })[s] || s
const typeIcon = (t) =>
  ({
    insurance: 'mdi-shield',
    product: 'mdi-package-variant',
    insurance_cancellation: 'mdi-calendar-remove',
  })[t] || 'mdi-bell'

async function load() {
  loading.value = true
  try {
    items.value = await notificationsApi.list()
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Laden fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  } finally {
    loading.value = false
  }
}

async function sendTest() {
  testing.value = true
  try {
    await notificationsApi.test()
    snack.value = { show: true, color: 'success', text: 'Test-Push gesendet — prüfe dein Handy.' }
  } catch (e) {
    snack.value = { show: true, color: 'error', text: e.response?.data?.detail || 'Test-Push fehlgeschlagen.' }
  } finally {
    testing.value = false
  }
}

onMounted(load)
</script>
