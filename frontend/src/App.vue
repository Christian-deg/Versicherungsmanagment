<template>
  <v-app>
    <v-app-bar color="primary" density="compact">
      <v-app-bar-nav-icon
        aria-label="Navigation öffnen"
        :aria-expanded="drawer ? 'true' : 'false'"
        aria-controls="main-navigation-drawer"
        @click="drawer = !drawer"
        class="d-md-none"
      />
      <v-app-bar-title class="d-flex align-center">
        <v-icon icon="mdi-shield-check" class="mr-2" />
        <div>
          <div>Versicherungs-Assistent</div>
          <div class="text-caption text-primary-lighten-5 d-none d-sm-block">
            Verträge, Garantien und KI-Auswertung an einem Ort
          </div>
        </div>
      </v-app-bar-title>
      <v-autocomplete
        v-model="searchSelection"
        :items="searchItems"
        :loading="searchLoading"
        class="d-none d-md-flex mr-2 flex-grow-0"
        style="width: 280px"
        density="compact"
        variant="solo-filled"
        flat
        hide-details
        clearable
        placeholder="Vertrag oder Produkt suchen…"
        prepend-inner-icon="mdi-magnify"
        item-title="title"
        return-object
        no-data-text="Keine Treffer"
        @update:focused="(focused) => focused && loadSearchData()"
        @update:model-value="onSearchSelect"
      />
      <v-btn
        class="d-none d-sm-flex"
        color="primary-lighten-5"
        variant="text"
        prepend-icon="mdi-cloud-upload"
        to="/upload"
      >
        Schnell hochladen
      </v-btn>
      <v-btn
        :icon="isDark ? 'mdi-white-balance-sunny' : 'mdi-weather-night'"
        :aria-label="isDark ? 'Helles Design aktivieren' : 'Dunkles Design aktivieren'"
        variant="text"
        @click="toggleTheme"
      />
    </v-app-bar>

    <v-navigation-drawer
      id="main-navigation-drawer"
      v-model="drawer"
      :permanent="mdAndUp"
      :temporary="!mdAndUp"
      width="280"
    >
      <div class="pa-4 border-b">
        <div class="text-overline text-medium-emphasis">Einfach starten</div>
        <div class="text-h6">Was möchtest du als Nächstes tun?</div>
        <div class="text-body-2 text-medium-emphasis mt-1">
          Dokumente prüfen, Verträge pflegen oder dem Assistenten Fragen stellen.
        </div>
      </div>

      <v-list nav class="py-2">
        <v-list-subheader>Navigation</v-list-subheader>
        <v-list-item
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          :prepend-icon="item.icon"
          :title="item.title"
          :subtitle="item.description"
          color="primary"
          rounded="lg"
          @click="onNavigate"
        />
      </v-list>

      <template #append>
        <div class="pa-4">
          <v-card color="primary" rounded="lg" variant="tonal">
            <v-card-text>
              <div class="text-subtitle-2 mb-2">Empfohlener Ablauf</div>
              <ol class="pl-4 text-body-2">
                <li>Police hochladen</li>
                <li>Daten kurz prüfen</li>
                <li>Fristen im Dashboard verfolgen</li>
              </ol>
              <v-btn class="mt-3" color="primary" block prepend-icon="mdi-cloud-upload" to="/upload">
                Jetzt Dokument hinzufügen
              </v-btn>
            </v-card-text>
          </v-card>
        </div>
      </template>
    </v-navigation-drawer>

    <v-main>
      <v-container fluid class="pa-4">
        <!-- key=path: erzwingt Neuladen beim Wechsel zwischen Detailseiten
             (z.B. /insurances/3 → /insurances/5), sonst bleibt alter Inhalt stehen -->
        <router-view :key="route.path" />
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDisplay, useTheme } from 'vuetify'
import { insurancesApi, productsApi } from './api'
import { categoryIcon, navItems, productIcon } from './constants'

const { mdAndUp } = useDisplay()
// Auf Desktop initial offen — sonst bleibt der permanente Drawer nach einem
// frischen Seitenaufruf unsichtbar (v-model=false schlägt das permanent-Prop).
const drawer = ref(mdAndUp.value)
const nav = navItems

// Dark Mode: gespeicherte Wahl > System-Einstellung > hell
const theme = useTheme()
const THEME_KEY = 'versicherung-theme'
const saved = localStorage.getItem(THEME_KEY)
const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)')?.matches
theme.global.name.value = saved === 'dark' || saved === 'light' ? saved : prefersDark ? 'dark' : 'light'

const isDark = computed(() => theme.global.current.value.dark)

function toggleTheme() {
  const next = isDark.value ? 'light' : 'dark'
  theme.global.name.value = next
  localStorage.setItem(THEME_KEY, next)
}

function onNavigate() {
  if (!mdAndUp.value) {
    drawer.value = false
  }
}

// Globale Suche: Verträge und Produkte, Treffer führen direkt zum Ziel
const router = useRouter()
const route = useRoute()
const searchSelection = ref(null)
const searchItems = ref([])
const searchLoading = ref(false)

async function loadSearchData() {
  searchLoading.value = true
  try {
    const [insurances, products] = await Promise.all([insurancesApi.list(), productsApi.list()])
    searchItems.value = [
      ...insurances.map((i) => ({
        title: `${i.name} (${i.versicherer})`,
        props: { prependIcon: categoryIcon(i.kategorie), subtitle: 'Versicherung' },
        route: `/insurances/${i.id}`,
      })),
      ...products
        .filter((p) => !p.archived)
        .map((p) => ({
          title: p.name,
          props: { prependIcon: productIcon(p.kategorie), subtitle: 'Produkt / Garantie' },
          route: `/products/${p.id}`,
        })),
    ]
  } catch {
    /* Suche ist nur Komfort — Fehler still ignorieren */
  } finally {
    searchLoading.value = false
  }
}

function onSearchSelect(selection) {
  if (!selection) return
  router.push(selection.route)
  nextTick(() => {
    searchSelection.value = null
  })
}
</script>
