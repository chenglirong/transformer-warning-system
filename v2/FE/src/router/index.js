import { createRouter, createWebHistory } from 'vue-router'

// v2 路由 —— SCADA 壳(侧栏+顶栏),页面挂 AppLayout 下
const routes = [
  {
    path: '/',
    component: () => import('@/layout/AppLayout.vue'),
    children: [
      { path: '', redirect: '/detect' },
      {
        path: 'detect',
        name: 'detect',
        component: () => import('@/views/DetectView.vue'),
        meta: {
          title: '气体分级检测',
          sub: 'DL/T 1498.2 表A.3 四档落档 · 注意值2 对齐 722 表3',
        },
      },
      {
        path: 'trend',
        name: 'trend',
        component: () => import('@/views/TrendView.vue'),
        meta: {
          title: '产气趋势预警',
          sub: '产气速率 §9.3.2 + 「预」提前预警 §9.3.3a · 辅线',
        },
      },
      {
        path: 'warning',
        name: 'warning',
        component: () => import('@/views/WarningView.vue'),
        meta: {
          title: '告警记录',
          sub: '四档全报 · 超标判据 /「预」/ 处置紧急度 / 故障类型',
        },
      },
      {
        path: 'diagnose',
        name: 'diagnose',
        component: () => import('@/views/DiagnoseView.vue'),
        meta: {
          title: '故障类型判断',
          sub: '特征气体 + 三比值 + 大卫三角 · 仅注意值2及以上触发',
        },
      },
      {
        path: 'agent',
        name: 'agent',
        component: () => import('@/views/AgentView.vue'),
        meta: {
          title: 'Agent 分析编排',
          sub: '七步竖向串联 · §10.3 · 表 G.1 报告（规则模板降级）',
        },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
