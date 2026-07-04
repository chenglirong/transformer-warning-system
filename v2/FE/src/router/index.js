import { createRouter, createWebHistory } from 'vue-router'

// v2 路由 —— 待按新模块补齐(检测/诊断/告警/趋势/Agent 页面)
const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
