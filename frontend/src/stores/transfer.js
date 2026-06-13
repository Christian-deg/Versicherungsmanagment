import { defineStore } from 'pinia'

/**
 * Übergibt eine bereits ausgewählte Datei zwischen Views — z. B. wenn die
 * Dokumenttyp-Erkennung auf der Upload-Seite eine Rechnung erkennt und in
 * den Rechnungs-Ablauf weiterleitet (File-Objekte passen nicht in die URL).
 */
export const useTransferStore = defineStore('transfer', {
  state: () => ({
    pendingInvoiceFile: null,
  }),
  actions: {
    setPendingInvoiceFile(file) {
      this.pendingInvoiceFile = file
    },
    takePendingInvoiceFile() {
      const f = this.pendingInvoiceFile
      this.pendingInvoiceFile = null
      return f
    },
  },
})
