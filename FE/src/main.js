import { createApp } from 'vue'
import 'iconify-icon'
import router from './router'
import App from './App.vue'
import './assets/styles/global.css'

const app = createApp(App)
app.use(router)
app.mount('#app')
