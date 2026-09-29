<template>
  <div>
    <v-skeleton-loader v-if="loading" type="article" />

    <template v-else-if="item">
      <div class="d-flex flex-column flex-md-row align-start align-md-center mb-4 ga-3">
        <div>
          <div class="d-flex align-center ga-2 flex-wrap">
            <v-btn icon="mdi-arrow-left" variant="text" aria-label="Zurück zur Liste" to="/products" />
            <h1 class="text-h4">{{ item.name }}</h1>
            <v-chip v-if="item.archived" color="grey" size="small" prepend-icon="mdi-archive">archiviert</v-chip>
          </div>
          <p class="text-medium-emphasis mt-1 ml-md-12">{{ item.kategorie }}</p>
        </div>
        <v-spacer />
        <div class="d-flex flex-wrap ga-2">
          <v-btn
            variant="outlined"
            prepend-icon="mdi-robot"
            :to="{ path: '/chat', query: { context: item.name } }"
          >
            Frage zum Produkt
          </v-btn>
          <v-btn variant="outlined" prepend-icon="mdi-pencil" @click="editDialog = true">Bearbeiten</v-btn>
          <v-btn
            variant="outlined"
            :prepend-icon="item.archived ? 'mdi-archive-arrow-up' : 'mdi-archive-arrow-down'"
            @click="toggleArchive"
          >
            {{ item.archived ? 'Reaktivieren' : 'Archivieren' }}
          </v-btn>
          <v-btn variant="outlined" color="error" prepend-icon="mdi-delete" @click="deleteDialog = true">Löschen</v-btn>
        </div>
      </div>

      <v-alert v-if="item.archived" type="info" variant="tonal" class="mb-4">
        Dieses Produkt ist archiviert (verkauft/entsorgt): keine Garantie-Warnungen, nicht in der
        Ampel — die Belege bleiben bis zum Ende ihrer Aufbewahrungsfrist erhalten.
      </v-alert>
      <v-alert v-else-if="issues.length" type="warning" variant="tonal" class="mb-4">
        <div v-for="issue in issues" :key="issue">• {{ issue }}</div>
      </v-alert>

      <v-row>
        <!-- Stammdaten + Garantie -->
        <v-col cols="12" md="6">
          <v-card height="100%">
            <v-card-title>
              <v-icon :icon="productIcon(item.kategorie)" class="mr-2" />Stammdaten & Garantie
            </v-card-title>
            <v-card-text>
              <v-list density="compact">
                <v-list-item title="Kategorie">
                  <template #append>
                    <v-chip size="small" color="primary" :prepend-icon="productIcon(item.kategorie)">
                      {{ item.kategorie }}
                    </v-chip>
                  </template>
                </v-list-item>
                <v-list-item v-if="item.seriennummer" title="Seriennummer">
                  <template #append>
                    <code>{{ item.seriennummer }}</code>
                  </template>
                </v-list-item>
                <v-list-item title="Kaufdatum">
                  <template #append>{{ item.purchase_date ? formatDate(item.purchase_date) : '–' }}</template>
                </v-list-item>
                <v-list-item title="Garantieende">
                  <template #append>
                    <v-chip v-if="item.warranty_end" size="small" :color="expiryColor(item.warranty_end)">
                      {{ formatDate(item.warranty_end) }} · {{ daysLabel(item.warranty_end) }}
                    </v-chip>
                    <span v-else class="text-medium-emphasis">nicht hinterlegt</span>
                  </template>
                </v-list-item>
                <v-list-item v-if="item.linked_insurance_id" title="Versicherung">
                  <template #append>
                    <router-link
                      :to="`/insurances/${item.linked_insurance_id}`"
                      class="text-decoration-none text-primary"
                    >
                      {{ insuranceName }}
                    </router-link>
                  </template>
                </v-list-item>
              </v-list>

              <!-- Restgarantie als Fortschrittsbalken -->
              <template v-if="warrantyProgress != null">
                <div class="text-subtitle-2 mt-3 mb-1">Restgarantie</div>
                <v-progress-linear
                  :model-value="warrantyProgress"
                  :color="expiryColor(item.warranty_end)"
                  height="10"
                  rounded
                />
                <div class="text-caption text-medium-emphasis mt-1">
                  {{ Math.round(warrantyProgress) }} % der Garantiezeit verstrichen ·
                  {{ daysLabel(item.warranty_end) }}
                </div>
              </template>

              <div v-if="item.notes" class="mt-3">
                <div class="text-subtitle-2 mb-1">Notizen</div>
                <p class="text-body-2" style="white-space: pre-wrap">{{ item.notes }}</p>
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Belege -->
        <v-col cols="12" md="6">
          <v-card height="100%">
            <v-card-title class="d-flex align-center">
              <v-icon icon="mdi-receipt-text" class="mr-2" />Kaufbelege
            </v-card-title>
            <v-card-text>
              <div class="d-flex flex-column flex-sm-row ga-2 align-sm-center mb-4">
                <v-file-input
                  v-model="newInvoiceFile"
                  label="Beleg hochladen (PDF, PNG, JPG)"
                  accept="application/pdf,image/png,image/jpeg"
                  density="comfortable"
                  hide-details
                  prepend-icon="mdi-paperclip"
                />
                <v-btn color="primary" prepend-icon="mdi-robot" :disabled="!hasNewInvoiceFile" @click="uploadInvoice">
                  Hochladen &amp; analysieren
                </v-btn>
              </div>

              <v-list v-if="invoices.length" lines="two" density="compact">
                <v-list-item v-for="inv in invoices" :key="inv.id">
                  <template #prepend>
                    <v-icon :icon="inv.mime_type === 'application/pdf' ? 'mdi-file-pdf-box' : 'mdi-file-image'" />
                  </template>
                  <v-list-item-title class="text-wrap">{{ inv.original_filename }}</v-list-item-title>
                  <v-list-item-subtitle>
                    {{ inv.purchase_date ? `Gekauft am ${formatDate(inv.purchase_date)}` : 'Kaufdatum unbekannt' }}
                    <template v-if="inv.amount_eur != null"> · {{ formatCurrency(inv.amount_eur) }}</template>
                    · Aufbewahrung bis {{ formatDate(inv.retain_until) }}
                  </v-list-item-subtitle>
                  <template #append>
                    <v-btn
                      icon="mdi-open-in-new"
                      size="small"
                      variant="text"
                      aria-label="Beleg ansehen"
                      :href="`/api/invoices/${inv.id}/file`"
                      target="_blank"
                    />
                    <v-btn
                      icon="mdi-download"
                      size="small"
                      variant="text"
                      aria-label="Beleg herunterladen"
                      :href="`/api/invoices/${inv.id}/download`"
                    />
                    <v-btn
                      icon="mdi-pencil"
                      size="small"
                      variant="text"
                      aria-label="Beleg bearbeiten"
                      @click="openInvoiceEdit(inv)"
                    />
                    <v-btn
                      icon="mdi-delete"
                      size="small"
                      variant="text"
                      color="error"
                      @click="confirmInvoiceDelete(inv)"
                    />
                  </template>
                </v-list-item>
              </v-list>
              <p v-else class="text-medium-emphasis mb-0">
                Noch kein Beleg hinterlegt — im Garantiefall ist der Kaufbeleg dein Nachweis.
              </p>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <ProductFormDialog v-model="editDialog" :product="item" @saved="onSaved" />

      <!-- Produkt löschen -->
      <v-dialog v-model="deleteDialog" max-width="440">
        <v-card>
          <v-card-title>Produkt löschen</v-card-title>
          <v-card-text>
            Möchtest du <strong>„{{ item.name }}"</strong> wirklich löschen?
            <v-alert type="warning" variant="tonal" density="compact" class="mt-3">
              Alle zugehörigen Belege werden mitgelöscht — auch bei laufender
              Aufbewahrungsfrist. Wenn du das Gerät nur nicht mehr besitzt,
              ist <strong>Archivieren</strong> die bessere Wahl: Belege bleiben erhalten.
            </v-alert>
          </v-card-text>
          <v-card-actions>
            <v-btn prepend-icon="mdi-archive-arrow-down" @click="deleteDialog = false; toggleArchive()">
              Lieber archivieren
            </v-btn>
            <v-spacer />
            <v-btn @click="deleteDialog = false">Abbrechen</v-btn>
            <v-btn color="error" @click="onDelete">Löschen</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <!-- Beleg löschen (mit Fristprüfung) -->
      <v-dialog v-model="invoiceDeleteDialog" max-width="460">
        <v-card>
          <v-card-title>Beleg löschen</v-card-title>
          <v-card-text>
            Möchtest du <strong>„{{ invoiceDeleteTarget?.original_filename }}"</strong> wirklich löschen?
            <template v-if="invoiceDeleteNeedsForce">
              <v-alert type="warning" variant="tonal" density="compact" class="mt-3">
                Die Aufbewahrungsfrist läuft noch bis
                <strong>{{ formatDate(invoiceDeleteTarget?.retain_until) }}</strong>.
              </v-alert>
              <v-checkbox
                v-model="forceInvoiceDelete"
                density="compact"
                hide-details
                label="Trotz laufender Aufbewahrungsfrist löschen"
              />
            </template>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn @click="invoiceDeleteDialog = false">Abbrechen</v-btn>
            <v-btn color="error" :disabled="invoiceDeleteNeedsForce && !forceInvoiceDelete" @click="onInvoiceDelete">
              Löschen
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </template>

    <v-empty-state
      v-else
      headline="Produkt nicht gefunden"
      text="Das Produkt existiert nicht (mehr)."
      icon="mdi-package-variant-remove"
    >
      <template #actions>
        <v-btn color="primary" to="/products">Zur Produktliste</v-btn>
      </template>
    </v-empty-state>

    <InvoiceEditDialog v-model="invoiceEditDialog" :invoice="invoiceEditTarget" @saved="onInvoiceEdited" />

    <v-snackbar v-model="snack.show" :color="snack.color">{{ snack.text }}</v-snackbar>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { insurancesApi, invoicesApi, productsApi } from '../api'
import InvoiceEditDialog from '../components/InvoiceEditDialog.vue'
import ProductFormDialog from '../components/ProductFormDialog.vue'
import { productIcon } from '../constants'
import { useTransferStore } from '../stores/transfer'
import { daysLabel, daysUntil, expiryColor, formatCurrency, formatDate, productQualityIssues } from '../utils'

const route = useRoute()
const router = useRouter()
const transfer = useTransferStore()

const item = ref(null)
const invoices = ref([])
const insurances = ref([])
const loading = ref(true)
const editDialog = ref(false)
const deleteDialog = ref(false)
const newInvoiceFile = ref(null)
const invoiceDeleteDialog = ref(false)
const invoiceDeleteTarget = ref(null)
const forceInvoiceDelete = ref(false)
const snack = ref({ show: false, color: 'success', text: '' })

const productId = Number(route.params.id)

const issues = computed(() => (item.value ? productQualityIssues(item.value, invoices.value.length > 0) : []))
const insuranceName = computed(() => {
  const ins = insurances.value.find((i) => i.id === item.value?.linked_insurance_id)
  return ins ? `${ins.name} (${ins.versicherer})` : `Versicherung #${item.value?.linked_insurance_id}`
})
const hasNewInvoiceFile = computed(() => {
  const f = newInvoiceFile.value
  return Array.isArray(f) ? f.length > 0 : Boolean(f)
})
// Verstrichene Garantiezeit in Prozent (nur mit Kaufdatum + Garantieende berechenbar)
const warrantyProgress = computed(() => {
  if (!item.value?.purchase_date || !item.value?.warranty_end) return null
  const start = new Date(item.value.purchase_date).getTime()
  const end = new Date(item.value.warranty_end).getTime()
  if (end <= start) return null
  const pct = ((Date.now() - start) / (end - start)) * 100
  return Math.min(100, Math.max(0, pct))
})
const invoiceDeleteNeedsForce = computed(() => {
  const d = daysUntil(invoiceDeleteTarget.value?.retain_until)
  return d != null && d > 0
})

async function load() {
  loading.value = true
  try {
    const [product, productInvoices, allInsurances] = await Promise.all([
      productsApi.get(productId),
      invoicesApi.list(productId),
      insurancesApi.list(),
    ])
    item.value = product
    invoices.value = productInvoices
    insurances.value = allInsurances
  } catch (e) {
    if (e.response?.status !== 404) {
      snack.value = { show: true, color: 'error', text: 'Laden fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
    }
    item.value = null
  } finally {
    loading.value = false
  }
}

async function onSaved() {
  snack.value = { show: true, color: 'success', text: 'Produkt gespeichert' }
  await load()
}

async function toggleArchive() {
  try {
    const payload = { ...item.value, archived: !item.value.archived }
    delete payload.id
    delete payload.created_at
    await productsApi.update(productId, payload)
    snack.value = {
      show: true,
      color: 'success',
      text: payload.archived ? 'Produkt archiviert — Belege bleiben erhalten.' : 'Produkt reaktiviert.',
    }
    await load()
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Aktion fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  }
}

async function onDelete() {
  deleteDialog.value = false
  try {
    await productsApi.delete(productId)
    await router.push('/products')
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Löschen fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  }
}

// Nachträgliche Korrektur eines Belegs (z. B. vergessener Betrag)
const invoiceEditDialog = ref(false)
const invoiceEditTarget = ref(null)

function openInvoiceEdit(inv) {
  invoiceEditTarget.value = inv
  invoiceEditDialog.value = true
}

async function onInvoiceEdited() {
  snack.value = { show: true, color: 'success', text: 'Beleg aktualisiert.' }
  // Neu laden: ein ergänztes Kaufdatum kann auch das Produkt ändern
  await load()
}

// Beleg geht in den Rechnungs-Dialog: KI liest Kaufdatum/Betrag aus, der Nutzer
// prüft — danach zurück zu diesem Produkt (return=product)
function uploadInvoice() {
  const f = Array.isArray(newInvoiceFile.value) ? newInvoiceFile.value[0] : newInvoiceFile.value
  if (!f) return
  transfer.setPendingInvoiceFile(f)
  router.push({ path: '/invoices', query: { product: productId, return: 'product' } })
}

function confirmInvoiceDelete(inv) {
  invoiceDeleteTarget.value = inv
  forceInvoiceDelete.value = false
  invoiceDeleteDialog.value = true
}

async function onInvoiceDelete() {
  invoiceDeleteDialog.value = false
  try {
    await invoicesApi.delete(invoiceDeleteTarget.value.id, { force: invoiceDeleteNeedsForce.value })
    invoices.value = await invoicesApi.list(productId)
  } catch (e) {
    snack.value = { show: true, color: 'error', text: 'Löschen fehlgeschlagen: ' + (e.response?.data?.detail || e.message) }
  } finally {
    invoiceDeleteTarget.value = null
  }
}

onMounted(load)
</script>
