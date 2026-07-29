<script setup>
// SCADA 壳:侧栏 240 + sticky 顶栏 + 内容区(对齐 dga-ui-v2)
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const pageMeta = computed(() => ({
  title: route.meta?.title || '设备状态分析智能体',
}))

const navGroups = [
  {
    label: '分析链路',
    items: [
      { path: '/dataset', title: '数据集', ready: true, icon: 'dataset' },
      { path: '/detect', title: '分级检测', ready: true, icon: 'detection' },
      { path: '/diagnose', title: '故障判型', ready: true, icon: 'diagnosis' },
      { path: '/trend', title: '产气趋势', ready: true, icon: 'trend' },
    ],
  },
  {
    label: '分析记录',
    items: [
      { path: '/warning', title: '告警列表', ready: true, icon: 'alerts' },
      { path: '/decision', title: '决策列表', ready: true, icon: 'decision' },
    ],
  },
  {
    label: '智能体',
    items: [
      { path: '/agent', title: 'Agent 分析', ready: true, icon: 'agent' },
      { path: '/knowledge', title: '判据知识库', ready: true, icon: 'knowledge' },
    ],
  },
]

function isActive(path) {
  return route.path === path || route.path.startsWith(path + '/')
}
</script>

<template>
  <div class="app">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-logo" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="#062521" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M13 2L3 14h7l-1 8 10-12h-7l1-8z" />
          </svg>
        </div>
        <div>
          <div class="brand-name">设备状态分析智能体</div>
          <div class="brand-sub">油中溶解气体 · 220kV 及以下</div>
        </div>
      </div>

      <nav class="nav">
        <div v-for="g in navGroups" :key="g.label" class="nav-group">
          <div class="nav-group-label">{{ g.label }}</div>
          <template v-for="item in g.items" :key="item.path">
            <router-link
              v-if="item.ready"
              :to="item.path"
              class="nav-item"
              :class="{ active: isActive(item.path) }"
            >
              <svg v-if="item.icon === 'trend'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                <path d="M3 17l6-6 4 4 8-8" /><path d="M17 7h4v4" />
              </svg>
              <svg v-else-if="item.icon === 'dataset'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                <ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5" /><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" />
              </svg>
              <svg v-else-if="item.icon === 'detection'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
                <circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3" />
              </svg>
              <svg v-else-if="item.icon === 'diagnosis'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2L2 7v10l10 5 10-5V7L12 2z" /><path d="M12 22V12M2 7l10 5 10-5" />
              </svg>
              <svg v-else-if="item.icon === 'alerts'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 3l9 16H3L12 3z" /><path d="M12 10v4M12 17v.5" />
              </svg>
              <svg v-else-if="item.icon === 'decision'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="4" width="18" height="16" rx="2" /><path d="M8 10h8M8 14h5" /><path d="M12 2v2" />
              </svg>
              <svg v-else-if="item.icon === 'knowledge'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                <path d="M8 7h8M8 11h6" />
              </svg>
              <svg v-else-if="item.icon === 'assistant'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z" />
                <path d="M8 9h8M8 13h5" />
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                <rect x="5" y="8" width="14" height="12" rx="2" /><path d="M12 8V4M9 2h6M9 14h.5M14.5 14h.5" />
              </svg>
              <span>{{ item.title }}</span>
            </router-link>
            <div v-else class="nav-item is-disabled">
              <svg v-if="item.icon === 'detection'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
                <circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3" />
              </svg>
              <svg v-else-if="item.icon === 'diagnosis'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2L2 7v10l10 5 10-5V7L12 2z" /><path d="M12 22V12M2 7l10 5 10-5" />
              </svg>
              <svg v-else-if="item.icon === 'alerts'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 3l9 16H3L12 3z" /><path d="M12 10v4M12 17v.5" />
              </svg>
              <svg v-else-if="item.icon === 'knowledge'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                <path d="M8 7h8M8 11h6" />
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                <rect x="5" y="8" width="14" height="12" rx="2" /><path d="M12 8V4M9 2h6M9 14h.5M14.5 14h.5" />
              </svg>
              <span>{{ item.title }}</span>
              <span class="soon-tag">待搭</span>
            </div>
          </template>
        </div>
      </nav>
    </aside>

    <div class="main">
      <header class="topbar">
        <div class="topbar-title">
          <h1>{{ pageMeta.title }}</h1>
        </div>
        <div class="topbar-spacer" />
      </header>
      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>
