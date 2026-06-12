<template>
  <div>
    <div class="d-flex flex-column flex-md-row align-start align-md-center mb-4 ga-3">
      <div>
        <h1 class="text-h4">Versicherungs-Assistent</h1>
        <p class="text-medium-emphasis mt-1">
          Stelle Fragen in Alltagssprache und erhalte Antworten mit Quellen aus deinen gespeicherten Daten.
        </p>
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
            :color="m.role === 'user' ? 'blue-lighten-5' : 'grey-lighten-4'"
            flat
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
        <div v-if="loading" class="text-center">
          <v-progress-circular indeterminate />
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
  </div>
</template>

<script setup>
import { nextTick, ref } from 'vue'
import { useDisplay } from 'vuetify'
import { chatApi } from '../api'
import { chatExampleQuestions } from '../constants'
import { confidenceColor } from '../utils'

const { smAndDown } = useDisplay()
const input = ref('')
const messages = ref([])
const loading = ref(false)
const exampleQuestions = chatExampleQuestions
const messagesContainer = ref(null)

const confColor = confidenceColor

async function onSend() {
  const frage = input.value.trim()
  if (!frage) return
  messages.value.push({ role: 'user', text: frage })
  scrollToBottom()
  input.value = ''
  loading.value = true
  try {
    const res = await chatApi.ask(frage)
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
    const container = messagesContainer.value
    container?.scrollTo?.({ top: container?.scrollHeight ?? 0, behavior: 'smooth' })
  })
}
</script>
