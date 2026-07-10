import { createRouter, createWebHistory } from 'vue-router'

// v2 路由 —— 后台管理骨架(左菜单+主内容),页面挂 AppLayout 下
const routes = [
  {
    path: '/',
    component: () => import('@/layout/AppLayout.vue'),
    children: [
      { path: '', redirect: '/trend' },
      { path: 'trend', name: 'trend', component: () => import('@/views/TrendView.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
