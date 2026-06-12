import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

export default api

export const insurancesApi = {
  list: () => api.get('/insurances').then(r => r.data),
  get: (id) => api.get(`/insurances/${id}`).then(r => r.data),
  create: (data) => api.post('/insurances', data).then(r => r.data),
  update: (id, data) => api.put(`/insurances/${id}`, data).then(r => r.data),
  delete: (id) => api.delete(`/insurances/${id}`),
  financial: () => api.get('/insurances/summary/financial').then(r => r.data),
}

export const productsApi = {
  list: () => api.get('/products').then(r => r.data),
  create: (data) => api.post('/products', data).then(r => r.data),
  update: (id, data) => api.put(`/products/${id}`, data).then(r => r.data),
  delete: (id) => api.delete(`/products/${id}`),
  warrantyStatus: () => api.get('/products/summary/warranty-status').then(r => r.data),
}

export const documentsApi = {
  upload: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/documents/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data)
  },
  uploadExtra: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/documents/upload-extra', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data)
  },
  confirm: (documentId, payload) =>
    api.post(`/documents/confirm/${documentId}`, payload).then(r => r.data),
  list: (insuranceId) =>
    api.get('/documents', { params: insuranceId != null ? { insurance_id: insuranceId } : {} }).then(r => r.data),
  attach: (insuranceId, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post(`/documents/attach/${insuranceId}`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data)
  },
  delete: (documentId) => api.delete(`/documents/${documentId}`),
  recommendation: (insuranceId) =>
    api.post(`/documents/${insuranceId}/recommendation`).then(r => r.data),
}

export const invoicesApi = {
  list: (productId) => api.get('/invoices', { params: productId != null ? { product_id: productId } : {} }).then(r => r.data),
  get: (id) => api.get(`/invoices/${id}`).then(r => r.data),
  analyze: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/invoices/analyze', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
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
  delete: (id) => api.delete(`/invoices/${id}`),
}

export const chatApi = {
  ask: (frage) => api.post('/chat', { frage }).then(r => r.data),
}
