<script setup>
// SCADA 壳:侧栏 240 + sticky 顶栏 + 内容区(对齐 dga-ui-v2)
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const pageMeta = computed(() => ({
  title: route.meta?.title || 'DGA 分析智能体',
}))

const navGroups = [
  {
    label: '分析链路',
    items: [
      { path: '/detect', title: '气体分级检测', ready: true, icon: 'detection' },
      { path: '/diagnose', title: '故障类型判断', ready: true, icon: 'diagnosis' },
      { path: '/trend', title: '产气趋势预警', ready: true, icon: 'trend' },
      { path: '/warning', title: '告警记录', ready: true, icon: 'alerts' },
    ],
  },
  {
    label: '智能体',
    items: [
      { path: '/agent', title: 'Agent 分析编排', ready: true, icon: 'agent' },
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
          <div class="brand-name">DGA 分析智能体</div>
          <div class="brand-sub">220kV 及以下 · 站端后台</div>
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
              <svg v-else-if="item.icon === 'detection'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
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
