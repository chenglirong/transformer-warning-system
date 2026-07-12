import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import router from './router'
import App from './App.vue'
// 设计令牌在前,Tailwind/覆盖在后(global.css)
import './assets/styles/tokens.css'
import './assets/styles/shell.css'
import './assets/styles/components.css'
import './assets/styles/overview.css'
import './assets/styles/global.css'

const app = createApp(App)
app.use(router)
app.use(ElementPlus)
app.mount('#app')
