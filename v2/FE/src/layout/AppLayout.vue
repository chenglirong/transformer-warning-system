<script setup>
// v2 后台管理骨架:左菜单 + 主内容区(非大屏,贴题后台软件)
import { useRoute } from 'vue-router'
const route = useRoute()

// 规划页面:检测/诊断/告警/趋势/Agent。已实现的先亮,未搭的留位
const menus = [
  { index: '/detect', title: '检测分级', ready: false },
  { index: '/trend', title: '趋势预警', ready: true },
  { index: '/diagnose', title: '故障类型判断', ready: false },
  { index: '/warning', title: '预警告警', ready: false },
  { index: '/agent', title: 'Agent 分析报告', ready: false },
]
</script>

<template>
  <el-container class="app-layout">
    <el-aside width="200px" class="aside">
      <div class="logo">DGA 分析智能体后台</div>
      <el-menu :default-active="route.path" router>
        <el-menu-item v-for="m in menus" :key="m.index" :index="m.index"
                      :disabled="!m.ready">
          <span>{{ m.title }}</span>
          <el-tag v-if="!m.ready" size="small" type="info" class="soon">待搭</el-tag>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-main class="main">
      <router-view />
    </el-main>
  </el-container>
</template>

<style scoped>
.app-layout { height: 100vh; }
.aside { background: #1f2937; color: #e5e7eb; }
.logo { padding: 18px 16px; font-size: 15px; font-weight: 600; color: #fff;
  border-bottom: 1px solid #374151; }
.aside :deep(.el-menu) { background: transparent; border-right: none; }
.aside :deep(.el-menu-item) { color: #cbd5e1; }
.aside :deep(.el-menu-item.is-active) { color: #fff; background: #374151; }
.soon { margin-left: 8px; transform: scale(0.85); }
.main { background: #f5f7fa; padding: 20px; }
</style>
