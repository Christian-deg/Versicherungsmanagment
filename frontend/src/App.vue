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
      <v-btn
        class="d-none d-sm-flex"
        color="primary-lighten-5"
        variant="text"
        prepend-icon="mdi-cloud-upload"
        to="/upload"
      >
        Schnell hochladen
      </v-btn>
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
          <v-card color="grey-lighten-4" rounded="lg" variant="flat">
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
        <router-view />
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { ref } from 'vue'
import { useDisplay } from 'vuetify'
import { navItems } from './constants'

const { mdAndUp } = useDisplay()
// Auf Desktop initial offen — sonst bleibt der permanente Drawer nach einem
// frischen Seitenaufruf unsichtbar (v-model=false schlägt das permanent-Prop).
const drawer = ref(mdAndUp.value)
const nav = navItems

function onNavigate() {
  if (!mdAndUp.value) {
    drawer.value = false
  }
}
</script>
