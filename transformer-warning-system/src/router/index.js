import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'dashboard', component: () => import('@/views/DashboardView.vue') },
  { path: '/alert-management', name: 'alert-management', component: () => import('@/views/AlertManagementView.vue') },
  { path: '/auxiliary-system', name: 'auxiliary-system', component: () => import('@/views/AuxiliarySystemView.vue') },
  { path: '/environment-monitoring', name: 'environment-monitoring', component: () => import('@/views/EnvironmentMonitoringView.vue') },
  { path: '/insulation-performance', name: 'insulation-performance', component: () => import('@/views/InsulationPerformanceView.vue') },
  { path: '/load-warning', name: 'load-warning', component: () => import('@/views/LoadWarningView.vue') },
  { path: '/mechanical-structure', name: 'mechanical-structure', component: () => import('@/views/MechanicalStructureView.vue') }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
