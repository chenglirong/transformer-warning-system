<template>
  <div class="h-screen flex flex-col">
    <AppHeader title="冷 却 与 辅 助 系 统 监 测" icon="mdi:fan" subtitle="维度 4 / 5" />

    <section class="px-3 pt-3 grid grid-cols-5 gap-3">
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">冷却风机</p>
            <p class="text-2xl font-bold text-green-400">15<span class="text-xs ml-1 text-gray-400">/16 运行</span></p>
          </div>
          <iconify-icon class="text-3xl text-green-400 fan-spin" icon="mdi:fan"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">1 台待机 · 0 故障</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">潜油泵</p>
            <p class="text-2xl font-bold text-yellow-400">7<span class="text-xs ml-1 text-gray-400">/8 运行</span></p>
          </div>
          <iconify-icon class="text-3xl text-yellow-400" icon="mdi:pump"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1"><span class="text-red-400">1 台故障停机</span> #1主变</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">进出口温差</p>
            <p class="text-2xl font-bold text-green-400">8.2<span class="text-xs ml-1">℃</span></p>
          </div>
          <iconify-icon class="text-3xl text-green-400" icon="mdi:thermometer-lines"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">报警 &lt;5℃（效率不足）</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">控制电源</p>
            <p class="text-2xl font-bold text-green-400">双路<span class="text-xs ml-1">正常</span></p>
          </div>
          <iconify-icon class="text-3xl text-green-400" icon="mdi:power-plug"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">主/备 自动切换已就绪</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">冷却效率</p>
            <p class="text-2xl font-bold text-cyan-400">94.2<span class="text-xs ml-1">%</span></p>
          </div>
          <iconify-icon class="text-3xl text-cyan-400" icon="mdi:speedometer"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">智能体学习基线 93.8%</p>
      </KpiCard>
    </section>

    <main class="flex-1 grid grid-cols-12 gap-3 p-3 overflow-hidden" style="min-height: 0">
      <!-- LEFT: cooling unit grid -->
      <div class="col-span-5 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 flex-1 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between">
            <span><iconify-icon icon="mdi:grid"></iconify-icon> 冷却单元阵列（16 风机 + 8 油泵）</span>
            <span class="text-[10px] text-gray-500">点击单元查看详情</span>
          </h3>
          <div class="grid grid-cols-4 gap-2 text-xs" style="height: calc(100% - 28px); overflow-y: auto">
            <div v-for="(u, i) in units" :key="i" class="unit-card" :class="u.state">
              <div class="flex items-center justify-between">
                <iconify-icon :class="u.iconClass" :icon="u.icon"></iconify-icon>
                <span class="text-[10px]" :class="u.labelClass">{{ u.label }}</span>
              </div>
              <p class="text-[11px] text-gray-400 mt-1">{{ u.title }}</p>
              <p class="text-[10px]" :class="u.subClass">{{ u.sub }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- CENTER: efficiency charts -->
      <div class="col-span-4 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 flex-1 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:chart-line"></iconify-icon> 冷却器进出口温差 24H
          </h3>
          <div class="w-full" style="height: calc(100% - 28px)">
            <EChart :option="diffOption" />
          </div>
        </div>
        <div class="glass rounded-lg p-3 flex-1 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:speedometer"></iconify-icon> 冷却效率 7 日（%）
          </h3>
          <div class="w-full" style="height: calc(100% - 28px)">
            <EChart :option="effOption" />
          </div>
        </div>
      </div>

      <!-- RIGHT: linkage + alerts -->
      <div class="col-span-3 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:link-variant"></iconify-icon> 冷却-油温 联动预警
          </h3>
          <div class="space-y-2 text-xs">
            <div class="bg-red-500/10 border border-red-500/30 rounded p-2">
              <p class="text-red-400 font-bold text-[11px]">⚠ 关联预警触发</p>
              <p class="text-gray-300 mt-1">#1主变 油温 ↑ 12℃ 但油泵 P2 未启动</p>
              <p class="text-[10px] text-gray-500 mt-1">自动处置：已启动备用泵，下发工单</p>
            </div>
            <div class="bg-gray-800/60 rounded p-2 border border-gray-700/60">
              <div class="flex justify-between mb-1">
                <span class="text-gray-400">冷却器清洗周期</span>
                <span class="text-cyan-400">距下次 12 日</span>
              </div>
              <div class="h-1.5 bg-gray-700 rounded overflow-hidden">
                <div class="h-full bg-cyan-400" style="width: 60%"></div>
              </div>
            </div>
          </div>
        </div>

        <div class="glass rounded-lg p-3 flex-1 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:clipboard-alert"></iconify-icon> 辅助系统预警 &amp; 处置建议
          </h3>
          <div class="space-y-2 overflow-y-auto" style="height: calc(100% - 28px)">
            <div v-for="(a, i) in alerts" :key="i" class="bg-gray-800/40 border-l-4 rounded p-2" :class="a.border">
              <div class="flex justify-between items-center mb-1">
                <span class="text-[10px] px-1.5 py-0.5 rounded" :class="a.tag">【{{ a.level }}】</span>
                <span class="text-[10px] text-gray-500">{{ a.time }}</span>
              </div>
              <p class="text-xs">{{ a.msg }}</p>
              <p class="text-[10px] text-cyan-300/80 mt-0.5">
                <iconify-icon icon="mdi:robot-outline"></iconify-icon> {{ a.action }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import AppHeader from '@/components/AppHeader.vue'
import KpiCard from '@/components/KpiCard.vue'
import EChart from '@/components/EChart.vue'
import { AXIS, TT } from '@/utils/chartDefaults'

const run      = { state: 'run',   icon: 'mdi:fan',     iconClass: 'text-green-400 fan-spin',  label: '运行', labelClass: 'text-green-400', subClass: 'text-gray-500' }
const warn     = { state: 'warn',  icon: 'mdi:fan',     iconClass: 'text-yellow-400 fan-spin', label: '预警', labelClass: 'text-yellow-400', subClass: 'text-yellow-400' }
const standby  = { state: '',      icon: 'mdi:fan-off', iconClass: 'text-gray-500',            label: '待机', labelClass: 'text-gray-500', subClass: 'text-gray-500' }
const pumpRun  = { state: 'run',   icon: 'mdi:pump',    iconClass: 'text-green-400',           label: '运行', labelClass: 'text-green-400', subClass: 'text-gray-500' }
const pumpFault= { state: 'fault', icon: 'mdi:pump-off',iconClass: 'text-red-400',             label: '故障', labelClass: 'text-red-400', subClass: 'text-red-400' }

const units = [
  { ...run,     title: 'F1 · 1485 rpm',  sub: '电流 2.1A' },
  { ...run,     title: 'F2 · 1492 rpm',  sub: '电流 2.0A' },
  { ...run,     title: 'F3 · 1480 rpm',  sub: '电流 2.2A' },
  { ...warn,    title: 'F4 · 1446 rpm',  sub: '电流 2.8A ↑' },
  { ...run,     title: 'F5 · 1488 rpm',  sub: '电流 2.1A' },
  { ...run,     title: 'F6 · 1490 rpm',  sub: '电流 2.0A' },
  { ...run,     title: 'F7 · 1483 rpm',  sub: '电流 2.1A' },
  { ...run,     title: 'F8 · 1496 rpm',  sub: '电流 2.0A' },
  { ...run,     title: 'F9 · 1485 rpm',  sub: '电流 2.1A' },
  { ...run,     title: 'F10 · 1492 rpm', sub: '电流 2.0A' },
  { ...standby, title: 'F11 · 0 rpm',    sub: '备用' },
  { ...run,     title: 'F12 · 1478 rpm', sub: '电流 2.2A' },
  { ...run,     title: 'F13~F16',        sub: '4 台运行中' },
  { ...pumpRun,   title: 'P1 · 0.45 MPa', sub: '流量 120 L/min' },
  { ...pumpFault, title: 'P2 · 停机',     sub: '电源中断' },
  { ...pumpRun,   title: 'P3~P8',         sub: '6 台正常' }
]

const diffOption = {
  tooltip: { trigger: 'axis', ...TT },
  legend: { textStyle: { color: '#9ca3af', fontSize: 10 }, top: 0, right: 0 },
  grid: { top: 25, bottom: 20, left: 35, right: 10 },
  xAxis: { type: 'category', data: ['00', '04', '08', '12', '16', '20', '24'], ...AXIS },
  yAxis: { type: 'value', ...AXIS, name: '℃', nameTextStyle: { color: '#9ca3af', fontSize: 10 } },
  series: [
    { name: '#1', type: 'line', smooth: true, data: [7.5, 7.2, 8.0, 9.2, 10.1, 8.5, 7.8], color: '#10b981' },
    { name: '#2', type: 'line', smooth: true, data: [8.2, 8.0, 8.8, 9.6, 10.5, 9.1, 8.5], color: '#06b6d4' },
    {
      name: '#3',
      type: 'line',
      smooth: true,
      data: [6.5, 6.2, 5.8, 5.1, 4.8, 5.3, 6.0],
      color: '#f59e0b',
      areaStyle: { opacity: 0.15 }
    },
    {
      name: '阈值 5℃',
      type: 'line',
      data: Array(7).fill(5),
      lineStyle: { type: 'dashed', color: '#ef4444' },
      symbol: 'none'
    }
  ]
}

const effOption = {
  tooltip: { trigger: 'axis', ...TT },
  grid: { top: 25, bottom: 20, left: 40, right: 10 },
  xAxis: { type: 'category', data: ['D-6', 'D-5', 'D-4', 'D-3', 'D-2', 'D-1', '今'], ...AXIS },
  yAxis: {
    type: 'value',
    ...AXIS,
    min: 85,
    max: 100,
    axisLabel: { ...AXIS.axisLabel, formatter: '{value}%' }
  },
  series: [
    {
      name: '冷却效率',
      type: 'line',
      smooth: true,
      data: [96.1, 95.8, 95.3, 94.9, 94.5, 94.3, 94.2],
      color: '#06b6d4',
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(6,182,212,.4)' },
            { offset: 1, color: 'rgba(6,182,212,0)' }
          ]
        }
      },
      markLine: {
        symbol: 'none',
        data: [{
          yAxis: 93.8,
          lineStyle: { color: '#f59e0b', type: 'dashed' },
          label: { formatter: '学习基线 93.8%', color: '#fcd34d', fontSize: 10 }
        }]
      }
    }
  ]
}

const alerts = [
  { level: '重要', tag: 'tag-org', border: 'border-orange-500', time: '09:15:30', msg: '#1主变 油泵 P2 故障停机 + 电源中断', action: '立即检修故障油泵，恢复电源，若冷却系统无法正常工作则停运变压器' },
  { level: '一般', tag: 'tag-yel', border: 'border-yellow-500', time: '08:42:15', msg: '#3主变 冷却器进出口温差 4.8℃（效率不足）', action: '检查冷却系统管路、控制回路，清理散热部件' },
  { level: '一般', tag: 'tag-yel', border: 'border-yellow-500', time: '07:20:00', msg: '#2主变 风机 F4 电流 2.8A 异常升高', action: '加强监测，预测轴承磨损，计划 48h 内检修' },
  { level: '提示', tag: 'tag-blu', border: 'border-blue-500', time: '06:00:00', msg: '冷却效率持续下降 0.6%（结合油温调整逻辑）', action: '智能体已联动下调油温预警阈值' }
]
</script>

<style scoped>
.fan-spin { animation: spin 2s linear infinite; }
@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

.unit-card {
  background: rgba(31, 41, 55, .5);
  border: 1px solid rgba(75, 85, 99, .4);
  border-radius: 6px;
  padding: 8px;
  position: relative;
}
.unit-card.run   { border-color: rgba(16, 185, 129, .5); }
.unit-card.fault { border-color: rgba(239, 68, 68, .6); box-shadow: inset 0 0 12px rgba(239, 68, 68, .15); }
.unit-card.warn  { border-color: rgba(245, 158, 11, .5); }
</style>
