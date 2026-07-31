import { createRouter, createWebHistory } from 'vue-router'

// v2 路由 —— SCADA 壳(侧栏+顶栏),页面挂 AppLayout 下
const routes = [
  {
    path: '/',
    component: () => import('@/layout/AppLayout.vue'),
    children: [
      { path: '', redirect: '/detect' },
      {
        path: 'dataset',
        name: 'dataset',
        component: () => import('@/views/DatasetView.vue'),
        meta: {
          title: '数据集',
          sub: '单台虚拟设备 × 360 天 · 7 气原始记录',
        },
      },
      {
        path: 'detect',
        name: 'detect',
        component: () => import('@/views/DetectView.vue'),
        meta: {
          title: '分级检测',
          sub: 'DL/T 1498.2 表A.3 四档落档 · 注意值2 对齐 722 表3',
        },
      },
      {
        path: 'trend',
        name: 'trend',
        component: () => import('@/views/TrendView.vue'),
        meta: {
          title: '产气趋势',
          sub: '§9.3.2 总烃月环比 · 涨势预警按 §9.3.3 a 当日超注意',
        },
      },
      {
        path: 'warning',
        name: 'warning',
        component: () => import('@/views/WarningView.vue'),
        meta: {
          title: '告警列表',
          sub: '四档全报 · 涨势预警 · 处置紧急度 · 故障类型摘要',
        },
      },
      {
        path: 'decision',
        name: 'decision',
        component: () => import('@/views/DecisionOverviewView.vue'),
        meta: {
          title: '决策列表',
          sub: '检测周期 · 二次采样 · 试验建议（全年流水）',
        },
      },
      {
        path: 'diagnose',
        name: 'diagnose',
        component: () => import('@/views/DiagnoseView.vue'),
        meta: {
          title: '故障判型',
          sub: '特征气体 + 三比值 + 大卫三角 · 注意值2 或速率超触发',
        },
      },
      {
        path: 'assistant',
        redirect: { name: 'agent', query: { assistant: '1' } },
      },
      {
        path: 'agent',
        name: 'agent',
        component: () => import('@/views/AgentView.vue'),
        meta: {
          title: 'Agent 分析',
          sub: '§10.3 流程串联 · 监测决策 · 表 G.1/G.2 报告',
        },
      },
      {
        path: 'knowledge',
        name: 'knowledge',
        component: () => import('@/views/KnowledgeView.vue'),
        meta: {
          title: '判据知识库',
          sub: '行业标准判据总表 · 条文原图可查',
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
