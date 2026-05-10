import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { router } from './router'
import { useRoleStore } from './stores/roleStore'
import './style.css'

const pinia = createPinia()
const app = createApp(App)

app.use(pinia)
useRoleStore().restoreRoleProfile()
app.use(router).mount('#app')
