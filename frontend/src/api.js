import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// Für KI-Analysen und große Uploads: die Dokumentenanalyse (Vision, bis zu
// 3 Evaluator-Retries) kann deutlich länger als 60 s dauern — mit dem
// Standard-Timeout bricht das Frontend ab, obwohl das Backend weiterarbeitet.
const LONG_TIMEOUT = 300000

export default api

export const insurancesApi = {
  list: () => api.get('/insurances').then(r => r.data),
  get: (id) => api.get(`/insurances/${id}`).then(r => r.data),
  create: (data) => api.post('/insurances', data).then(r => r.data),
  update: (id, data) => api.put(`/insurances/${id}`, data).then(r => r.data),
  delete: (id) => api.delete(`/insurances/${id}`),
  financial: () => api.get('/insurances/summary/financial').then(r => r.data),
  // Prämienverlauf aller Versicherungen (für Trend-Anzeigen und Detailseite)
  premiumHistory: () => api.get('/insurances/history/premiums').then(r => r.data),
}

export const productsApi = {
  list: () => api.get('/products').then(r => r.data),
  get: (id) => api.get(`/products/${id}`).then(r => r.data),
  create: (data) => api.post('/products', data).then(r => r.data),
  update: (id, data) => api.put(`/products/${id}`, data).then(r => r.data),
  delete: (id) => api.delete(`/products/${id}`),
  warrantyStatus: () => api.get('/products/summary/warranty-status').then(r => r.data),
}

export const documentsApi = {
  classify: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/documents/classify', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: LONG_TIMEOUT,
    }).then(r => r.data)
  },
  upload: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/documents/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: LONG_TIMEOUT,
    }).then(r => r.data)
  },
  uploadExtra: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/documents/upload-extra', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: LONG_TIMEOUT,
    }).then(r => r.data)
  },
  confirm: (documentId, payload) =>
    api.post(`/documents/confirm/${documentId}`, payload).then(r => r.data),
  // Duplikat-Erkennung: analysiertes Dokument einem bestehenden Vertrag zuordnen
  assign: (documentId, insuranceId) =>
    api.post(`/documents/assign/${documentId}`, { insurance_id: insuranceId }).then(r => r.data),
  list: (insuranceId) =>
    api.get('/documents', { params: insuranceId != null ? { insurance_id: insuranceId } : {} }).then(r => r.data),
  attach: (insuranceId, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post(`/documents/attach/${insuranceId}`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: LONG_TIMEOUT,
    }).then(r => r.data)
  },
  delete: (documentId) => api.delete(`/documents/${documentId}`),
  // GET: gespeicherte Empfehlung (null, wenn noch keine vorhanden)
  recommendationGet: (insuranceId) =>
    api.get(`/documents/${insuranceId}/recommendation`).then(r => r.data).catch((e) => {
      if (e.response?.status === 404) return null
      throw e
    }),
  // POST: Empfehlung neu erzeugen / erneuern (Agent mit Websuche — kann dauern)
  recommendation: (insuranceId) =>
    api.post(`/documents/${insuranceId}/recommendation`, null, { timeout: LONG_TIMEOUT }).then(r => r.data),
  // Suchindex-Konsistenzcheck: fehlende Dokumente werden im Hintergrund neu indiziert
  reindex: () => api.post('/documents/maintenance/reindex').then(r => r.data),
}

export const invoicesApi = {
  list: (productId) => api.get('/invoices', { params: productId != null ? { product_id: productId } : {} }).then(r => r.data),
  get: (id) => api.get(`/invoices/${id}`).then(r => r.data),
  analyze: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/invoices/analyze', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: LONG_TIMEOUT,
    }).then(r => r.data)
  },
  upload: (productId, file, { purchaseDate, amountEur, notes } = {}) => {
    const fd = new FormData()
    fd.append('product_id', productId)
    fd.append('file', file)
    if (purchaseDate) fd.append('purchase_date', purchaseDate)
    if (amountEur != null) fd.append('amount_eur', amountEur)
    if (notes) fd.append('notes', notes)
    return api.post('/invoices', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data)
  },
  delete: (id, { force = false } = {}) =>
    api.delete(`/invoices/${id}`, { params: force ? { force: true } : {} }),
}

export const chatApi = {
  ask: (frage, verlauf = []) =>
    api.post('/chat', { frage, verlauf }, { timeout: 120000 }).then(r => r.data),
}

export const notificationsApi = {
  list: (limit = 100) => api.get('/notifications', { params: { limit } }).then(r => r.data),
  test: () => api.post('/notifications/test').then(r => r.data),
}
