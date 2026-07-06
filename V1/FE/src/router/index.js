import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard',  name: 'dashboard',  component: () => import('@/views/DashboardView.vue') },
  // 以下页面待重建，临时指向现有文件
  { path: '/analysis',   name: 'analysis',   component: () => import('@/views/AnalysisView.vue') },
  { path: '/detection',  name: 'detection',  component: () => import('@/views/DetectionView.vue') },
  { path: '/prediction', name: 'prediction', component: () => import('@/views/PredictionView.vue') },
  { path: '/alerts',     name: 'alerts',     component: () => import('@/views/AlertsView.vue') }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
