import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { aliases, mdi } from 'vuetify/iconsets/mdi'
import VueApexCharts from 'vue3-apexcharts'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'

import App from './App.vue'
import Dashboard from './views/Dashboard.vue'
import Insurances from './views/Insurances.vue'
import Invoices from './views/Invoices.vue'
import Products from './views/Products.vue'
import Calendar from './views/Calendar.vue'
import Upload from './views/Upload.vue'
import Chat from './views/Chat.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: Dashboard, name: 'dashboard' },
    { path: '/insurances', component: Insurances, name: 'insurances' },
    { path: '/products', component: Products, name: 'products' },
    { path: '/invoices', component: Invoices, name: 'invoices' },
    { path: '/calendar', component: Calendar, name: 'calendar' },
    { path: '/upload', component: Upload, name: 'upload' },
    { path: '/chat', component: Chat, name: 'chat' },
  ],
})

const vuetify = createVuetify({
  components,
  directives,
  icons: { defaultSet: 'mdi', aliases, sets: { mdi } },
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        colors: {
          primary: '#1976d2',
          secondary: '#26a69a',
          error: '#d32f2f',
          warning: '#f9a825',
          success: '#43a047',
        },
      },
    },
  },
})

createApp(App)
  .use(createPinia())
  .use(router)
  .use(vuetify)
  .use(VueApexCharts)
  .mount('#app')
