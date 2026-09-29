<template>
  <v-combobox
    :model-value="modelValue"
    :items="items"
    label="Kategorie"
    hint="Aus der Liste wählen – nur wenn keine passt, eine neue eintippen"
    persistent-hint
    @update:model-value="(v) => emit('update:modelValue', v ?? '')"
    @blur="normalize"
  />
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { productsApi } from '../api'
import { productCategories } from '../constants'

const props = defineProps({
  modelValue: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

const used = ref([])

onMounted(async () => {
  try {
    used.value = (await productsApi.list()).map((p) => p.kategorie).filter(Boolean)
  } catch {
    used.value = []
  }
})

// Vorschläge + bereits verwendete Kategorien, ohne Dubletten (Groß-/Kleinschreibung
// egal), alphabetisch — "Sonstiges" als Auffangkategorie ans Ende
const items = computed(() => {
  const unique = new Map()
  for (const k of [...productCategories, ...used.value]) {
    const name = k.trim()
    if (name && !unique.has(name.toLowerCase())) unique.set(name.toLowerCase(), name)
  }
  return [...unique.values()].sort((a, b) =>
    a === 'Sonstiges' ? 1 : b === 'Sonstiges' ? -1 : a.localeCompare(b, 'de')
  )
})

// Eingetippten Wert an eine vorhandene Schreibweise angleichen — verhindert
// Dubletten wie "netzwerk" neben "Netzwerk". Erst beim Verlassen des Felds,
// damit Leerzeichen beim Tippen (z. B. "Konsole & Gaming") nicht verschwinden.
function normalize() {
  const text = (props.modelValue || '').trim()
  const match = items.value.find((k) => k.toLowerCase() === text.toLowerCase())
  const normalized = match || text
  if (normalized !== props.modelValue) emit('update:modelValue', normalized)
}
</script>
