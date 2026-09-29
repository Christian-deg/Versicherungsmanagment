<template>
  <div>
    <div class="d-flex flex-column flex-md-row align-start align-md-center mb-4 ga-3">
      <div>
        <h1 class="text-h4">Versicherungs-Assistent</h1>
        <p class="text-medium-emphasis mt-1">
          Stelle Fragen in Alltagssprache und erhalte Antworten mit Quellen aus deinen gespeicherten Daten.
        </p>
      </div>
      <v-spacer />
      <div class="d-flex ga-2">
        <v-tooltip text="Prüft, ob alle Dokumente im Suchindex sind, und indiziert Fehlende nach" location="bottom">
          <template #activator="{ props }">
            <v-btn
              v-bind="props"
              variant="outlined"
              prepend-icon="mdi-database-refresh"
              :loading="reindexing"
              @click="checkIndex"
            >
              Suchindex prüfen
            </v-btn>
          </template>
        </v-tooltip>
        <v-btn
          v-if="messages.length"
          variant="outlined"
          prepend-icon="mdi-broom"
          :disabled="loading"
          @click="newChat"
        >
          Neuer Chat
        </v-btn>
      </div>
    </div>

    <v-card class="mb-4" min-height="300">
      <v-card-text ref="messagesContainer" style="max-height: 60vh; overflow-y: auto">
        <div v-if="!messages.length" class="text-center text-medium-emphasis py-8">
          <v-icon size="64" color="primary">mdi-robot-happy</v-icon>
          <p class="mt-2 mb-4">Frag mich z.B. „Wann läuft meine KFZ-Versicherung ab?“</p>
          <div class="d-flex justify-center flex-wrap ga-2">
            <v-chip
              v-for="question in exampleQuestions"
              :key="question"
              color="primary"
              variant="outlined"
              class="text-wrap py-2"
              style="height: auto; white-space: normal"
              @click="sendExample(question)"
            >
              {{ question }}
            </v-chip>
          </div>
        </div>
        <div v-for="(m, idx) in messages" :key="idx" class="mb-3">
          <div :class="m.role === 'user' ? 'text-right' : ''">
            <v-chip :color="m.role === 'user' ? 'primary' : 'secondary'" class="mb-1">
              {{ m.role === 'user' ? 'Du' : 'Assistent' }}
            </v-chip>
          </div>
          <v-card
            :color="m.role === 'user' ? 'primary' : 'secondary'"
            variant="tonal"
            class="pa-3"
            :class="m.role === 'user' ? 'ml-auto' : ''"
            :max-width="smAndDown ? '95%' : '80%'"
          >
            <div style="white-space: pre-wrap">{{ m.text }}</div>
            <div v-if="m.quellen?.length" class="mt-2">
              <v-chip v-for="q in m.quellen" :key="q" size="x-small" class="mr-1">{{ q }}</v-chip>
            </div>
            <v-chip v-if="m.konfidenz" size="x-small" :color="confColor(m.konfidenz)" class="mt-1">
              Konfidenz: {{ m.konfidenz }}
            </v-chip>
          </v-card>
        </div>
        <div v-if="loading" class="d-flex align-center ga-3 pa-2">
          <v-progress-circular indeterminate size="20" width="2" color="primary" />
          <span class="text-medium-emphasis">{{ loadingText }}</span>
        </div>
      </v-card-text>
    </v-card>

    <v-card>
      <v-card-text>
        <div class="d-flex ga-2 align-end">
          <v-textarea
            v-model="input"
            label="Deine Frage..."
            variant="outlined"
            density="comfortable"
            rows="1"
            max-rows="6"
            auto-grow
            hide-details
            @keydown.enter.exact.prevent="onSend"
            @keydown.ctrl.enter.prevent="onSend"
            @keydown.meta.enter.prevent="onSend"
            :disabled="loading"
          />
          <v-btn
            color="primary"
            icon="mdi-send"
            aria-label="Frage senden"
            @click="onSend"
            :loading="loading"
            :disabled="!input.trim()"
          />
        </div>
        <div class="text-caption text-medium-emphasis mt-1 d-none d-sm-block">
          Enter zum Senden · Shift+Enter für neue Zeile
        </div>
      </v-card-text>
    </v-card>

    <v-snackbar v-model="snack.show" :color="snack.color" timeout="6000">{{ snack.text }}</v-snackbar>
  </div>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useDisplay } from 'vuetify'
import { chatApi, documentsApi } from '../api'
import { chatExampleQuestions } from '../constants'
import { confidenceColor } from '../utils'

const { smAndDown } = useDisplay()
const route = useRoute()
const input = ref('')

// Kontext-Einstieg von Detailseiten ("Frage zum Vertrag/Produkt"):
// Eingabefeld mit Bezug vorbefüllen, Frage formuliert der Nutzer selbst
if (typeof route.query.context === 'string' && route.query.context) {
  input.value = `Zu „${route.query.context}": `
}
const messages = ref([])
const loading = ref(false)
const exampleQuestions = chatExampleQuestions
const messagesContainer = ref(null)

// Verlauf überlebt Seitenwechsel (pro Browser-Tab) — vorher war der Chat nach
// jedem Navigieren weg
const STORAGE_KEY = 'versicherung-chat'
try {
  messages.value = JSON.parse(sessionStorage.getItem(STORAGE_KEY)) || []
} catch {
  messages.value = []
}
watch(
  messages,
  (v) => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(v))
    } catch {
      /* Speicher voll o.ä. — Persistenz ist nur Komfort */
    }
  },
  { deep: true }
)

function newChat() {
  messages.value = []
  sessionStorage.removeItem(STORAGE_KEY)
}

// Rotierender Status während der Agent arbeitet — die Antwort selbst kann nicht
// gestreamt werden, ohne den Output-Sicherheitsfilter zu umgehen (er prüft die
// vollständige Antwort, bevor sie den Server verlässt)
const loadingTexts = [
  'Durchsuche deine Dokumente…',
  'Prüfe Vertragsdaten…',
  'Formuliere Antwort…',
  'Gleich fertig…',
]
const loadingText = ref(loadingTexts[0])
let loadingTimer = null
watch(loading, (active) => {
  clearInterval(loadingTimer)
  if (active) {
    let i = 0
    loadingText.value = loadingTexts[0]
    loadingTimer = setInterval(() => {
      i = Math.min(i + 1, loadingTexts.length - 1)
      loadingText.value = loadingTexts[i]
    }, 3500)
  }
})

// Suchindex-Wartung: prüft die Vollständigkeit des Vektorindex und stößt
// fehlende Embeddings im Hintergrund neu an
const reindexing = ref(false)
const snack = ref({ show: false, color: 'success', text: '' })

async function checkIndex() {
  reindexing.value = true
  try {
    const res = await documentsApi.reindex()
    snack.value = {
      show: true,
      color: res.fehlend === 0 ? 'success' : 'info',
      text:
        res.fehlend === 0
          ? `Suchindex vollständig — alle ${res.dokumente} Dokumente sind indiziert.`
          : `${res.fehlend} von ${res.dokumente} Dokumenten fehlten im Index und werden jetzt nachindiziert — das kann einige Minuten dauern.`,
    }
  } catch (e) {
    snack.value = {
      show: true,
      color: 'error',
      text: 'Index-Prüfung fehlgeschlagen: ' + (e.response?.data?.detail || e.message),
    }
  } finally {
    reindexing.value = false
  }
}

const confColor = confidenceColor

// Wie viele bisherige Nachrichten als Kontext mitgeschickt werden
const HISTORY_LIMIT = 30

async function onSend() {
  const frage = input.value.trim()
  if (!frage) return
  // Verlauf vor der neuen Frage einfrieren — Fehlermeldungen gehören nicht in den Kontext
  const verlauf = messages.value
    .filter((m) => !m.isError)
    .slice(-HISTORY_LIMIT)
    .map((m) => ({ rolle: m.role === 'user' ? 'user' : 'assistant', text: m.text }))
  messages.value.push({ role: 'user', text: frage })
  scrollToBottom()
  input.value = ''
  loading.value = true
  try {
    const res = await chatApi.ask(frage, verlauf)
    messages.value.push({
      role: 'assistant',
      text: res.antwort,
      quellen: res.quellen,
      konfidenz: res.konfidenz,
    })
    scrollToBottom()
  } catch (e) {
    messages.value.push({
      role: 'assistant',
      text: 'Fehler: ' + (e.response?.data?.detail || e.message),
      konfidenz: 'low',
      isError: true,
    })
    scrollToBottom()
  } finally {
    loading.value = false
  }
}

function sendExample(question) {
  input.value = question
  onSend()
}

function scrollToBottom() {
  nextTick(() => {
    // Ref auf <v-card-text> liefert die Komponenteninstanz — scrollen muss das DOM-Element ($el)
    const el = messagesContainer.value?.$el
    el?.scrollTo?.({ top: el.scrollHeight, behavior: 'smooth' })
  })
}
</script>
