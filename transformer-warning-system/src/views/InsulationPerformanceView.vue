<template>
  <div class="h-screen flex flex-col">
    <AppHeader
      title="D G A 油 中 溶 解 气 体 分 析（早 期 预 警 核 心）"
      icon="mdi:test-tube"
      subtitle="维度 2 / 5"
    />

    <!-- 7 gas cards -->
    <section class="px-3 pt-3 grid grid-cols-7 gap-3">
      <div v-for="(g, i) in gases" :key="i" class="gas-card" :class="g.cls">
        <p class="text-[11px] text-gray-400">
          {{ g.sym }} <span class="text-gray-500">{{ g.zh }}</span>
        </p>
        <p class="text-2xl font-bold mt-1 flex items-center gap-1" :class="g.valueClass">
          <span>{{ g.value }}</span>
          <iconify-icon v-if="g.alert" class="text-sm pulse" icon="mdi:alert"></iconify-icon>
          <span class="text-xs ml-1 text-gray-500">{{ g.unit }}</span>
        </p>
        <p class="text-[10px] text-gray-500">
          {{ g.hint }} · <span :class="g.stateClass">{{ g.state }}</span>
        </p>
        <div class="h-1 bg-gray-700/60 rounded mt-2">
          <div class="h-1 rounded" :class="g.barClass" :style="{ width: g.width + '%' }"></div>
        </div>
      </div>
    </section>

    <main class="flex-1 grid grid-cols-12 gap-3 p-3 overflow-hidden" style="min-height: 0">
      <!-- LEFT: trends + rate + status -->
      <div class="col-span-8 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 1.3">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between">
            <span><iconify-icon icon="mdi:chart-multiline"></iconify-icon> 7 气体 30 日浓度趋势（ppm）</span>
            <span class="text-[10px] text-gray-500">预警：72h 内 ≥20% 持续上升</span>
          </h3>
          <div class="w-full" style="height: calc(100% - 28px)">
            <EChart :option="trendOption" />
          </div>
        </div>

        <div class="flex-1 grid grid-cols-2 gap-3 overflow-hidden">
          <div class="glass rounded-lg p-3 overflow-hidden">
            <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
              <iconify-icon icon="mdi:speedometer"></iconify-icon> 各气体 72H 产气速率（ppm/72h）
            </h3>
            <div class="w-full" style="height: calc(100% - 28px)">
              <EChart :option="rateOption" />
            </div>
          </div>
          <div class="glass rounded-lg p-3 overflow-hidden">
            <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
              <iconify-icon icon="mdi:oil"></iconify-icon> 在运变压器 DGA 状态分布
            </h3>
            <div class="w-full" style="height: calc(100% - 28px)">
              <EChart :option="statusOption" />
            </div>
          </div>
        </div>
      </div>

      <!-- RIGHT: IEC + Rogers + alerts -->
      <div class="col-span-4 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:calculator-variant"></iconify-icon> IEC 三比值法故障判定
          </h3>
          <div class="grid grid-cols-3 gap-2 text-xs text-center">
            <div v-for="r in ratios" :key="r.name" class="bg-gray-800/60 rounded p-2 border border-gray-700/60">
              <p class="text-[10px] text-gray-400">{{ r.name }}</p>
              <p class="text-base font-bold text-yellow-400">{{ r.value }}</p>
              <p class="text-[10px] text-gray-500">码：{{ r.code }}</p>
            </div>
          </div>
          <div class="mt-3 p-2 bg-orange-500/10 border border-orange-500/30 rounded">
            <p class="text-xs">
              <span class="text-orange-300 font-bold">判定结果：</span>
              <span class="text-white">编码 021 → 低温过热（&lt;300℃）</span>
            </p>
            <p class="text-[10px] text-gray-400 mt-1">智能体结合历史案例库，潜在故障概率 78%</p>
          </div>
        </div>

        <div class="glass rounded-lg p-3 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:chart-pie"></iconify-icon> 罗杰斯比值法交叉验证
          </h3>
          <div class="w-full" style="height: 160px">
            <EChart :option="rogerOption" />
          </div>
        </div>

        <div class="glass rounded-lg p-3 flex-1 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:clipboard-alert"></iconify-icon> DGA 预警 &amp; 智能体处置建议
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
import EChart from '@/components/EChart.vue'
import { AXIS, TT } from '@/utils/chartDefaults'

const gases = [
  { sym: 'H₂',    zh: '氢气',           value: '42.5', unit: 'ppm', hint: '阈值 150 ppm', state: '正常', stateClass: 'text-green-400', valueClass: 'text-green-400', barClass: 'bg-green-400', width: 28, cls: '', alert: false },
  { sym: 'CH₄',   zh: '甲烷',           value: '58.2', unit: 'ppm', hint: '7 日 ↑ 38%',    state: '关注', stateClass: 'text-green-400', valueClass: 'text-green-400', barClass: 'bg-green-400', width: 52, cls: '', alert: false },
  { sym: 'C₂H₆',  zh: '乙烷',           value: '22.8', unit: 'ppm', hint: '7 日 ↑ 27%',    state: '正常', stateClass: 'text-green-400', valueClass: 'text-green-400', barClass: 'bg-green-400', width: 32, cls: '', alert: false },
  { sym: 'C₂H₄',  zh: '乙烯（过热）',   value: '45.1', unit: 'ppm', hint: '72h ↑ 23%',     state: '预警', stateClass: 'text-yellow-400', valueClass: 'text-yellow-400', barClass: 'bg-yellow-400', width: 65, cls: 'warn',   alert: false },
  { sym: 'C₂H₂',  zh: '乙炔（放电）',   value: '3.24', unit: 'ppm', hint: '阈值 5 ppm',    state: '趋近报警', stateClass: 'text-red-400', valueClass: 'text-red-400',    barClass: 'bg-red-400',    width: 65, cls: 'danger', alert: true  },
  { sym: 'CO',    zh: '一氧化碳',       value: '312',  unit: 'ppm', hint: '固体绝缘老化指标', state: '',     stateClass: '', valueClass: 'text-green-400', barClass: 'bg-green-400', width: 42, cls: '', alert: false },
  { sym: 'CO₂',   zh: '二氧化碳',       value: '1840', unit: 'ppm', hint: 'CO₂/CO ≈ 5.9',  state: '正常', stateClass: 'text-green-400', valueClass: 'text-green-400', barClass: 'bg-green-400', width: 46, cls: '', alert: false }
]

const ratios = [
  { name: 'C₂H₂/C₂H₄', value: '0.072', code: 0 },
  { name: 'CH₄/H₂',    value: '1.37',  code: 2 },
  { name: 'C₂H₄/C₂H₆', value: '1.98',  code: 1 }
]

const days = Array.from({ length: 30 }, (_, i) => `D-${29 - i}`)
const gen = (start, end, wave = 0.1) =>
  days.map((_, i) => {
    const t = i / 29
    const v = start + (end - start) * t
    return +(v * (1 + (Math.random() - 0.5) * wave)).toFixed(1)
  })

const trendOption = {
  tooltip: { trigger: 'axis', ...TT },
  legend: { textStyle: { color: '#9ca3af', fontSize: 10 }, top: 0, right: 0, itemWidth: 10, itemHeight: 6 },
  grid: { top: 25, bottom: 30, left: 40, right: 50 },
  xAxis: { type: 'category', data: days, ...AXIS, axisLabel: { ...AXIS.axisLabel, interval: 4 } },
  yAxis: [
    { type: 'value', name: 'ppm',  nameTextStyle: { color: '#9ca3af', fontSize: 10 }, ...AXIS },
    { type: 'value', name: 'C₂H₂', nameTextStyle: { color: '#ef4444', fontSize: 10 }, ...AXIS, max: 6 }
  ],
  dataZoom: [{ type: 'inside' }, { type: 'slider', height: 12, bottom: 8, textStyle: { color: '#9ca3af' } }],
  series: [
    { name: 'H₂',   type: 'line', smooth: true, data: gen(25, 42.5), color: '#10b981' },
    { name: 'CH₄',  type: 'line', smooth: true, data: gen(35, 58.2), color: '#06b6d4' },
    { name: 'C₂H₆', type: 'line', smooth: true, data: gen(15, 22.8), color: '#8b5cf6' },
    { name: 'C₂H₄', type: 'line', smooth: true, data: gen(22, 45.1), color: '#f59e0b' },
    {
      name: 'C₂H₂（右）',
      type: 'line',
      smooth: true,
      yAxisIndex: 1,
      data: gen(0.8, 3.24, 0.2),
      color: '#ef4444',
      lineStyle: { width: 2.5 },
      markLine: {
        symbol: 'none',
        data: [{
          yAxis: 5,
          lineStyle: { color: '#dc2626', type: 'dashed' },
          label: { formatter: '报警 5ppm', color: '#fca5a5', fontSize: 10 }
        }]
      }
    }
  ]
}

const rateOption = {
  tooltip: { trigger: 'axis', ...TT },
  grid: { top: 20, bottom: 20, left: 50, right: 10 },
  xAxis: { type: 'value', ...AXIS, axisLabel: { ...AXIS.axisLabel, formatter: '{value}%' } },
  yAxis: { type: 'category', data: ['CO₂', 'CO', 'C₂H₂', 'C₂H₄', 'C₂H₆', 'CH₄', 'H₂'], ...AXIS },
  series: [{
    type: 'bar',
    data: [8, 12, 38, 23, 27, 18, 15],
    itemStyle: {
      color: (p) => (p.value >= 20 ? '#ef4444' : p.value >= 15 ? '#f59e0b' : '#10b981'),
      borderRadius: [0, 4, 4, 0]
    },
    label: { show: true, position: 'right', color: '#e5e7eb', fontSize: 10, formatter: '{c}%' },
    markLine: { symbol: 'none', data: [{ xAxis: 20, lineStyle: { color: '#ef4444', type: 'dashed' } }] }
  }]
}

const statusOption = {
  tooltip: { trigger: 'item', ...TT },
  legend: { bottom: 0, textStyle: { color: '#9ca3af', fontSize: 10 } },
  series: [{
    type: 'pie',
    radius: ['40%', '68%'],
    center: ['50%', '45%'],
    label: { color: '#cbd5e1', fontSize: 10, formatter: '{b}\n{d}%' },
    data: [
      { value: 98, name: '正常', itemStyle: { color: '#10b981' } },
      { value: 18, name: '关注', itemStyle: { color: '#06b6d4' } },
      { value: 8,  name: '预警', itemStyle: { color: '#f59e0b' } },
      { value: 3,  name: '报警', itemStyle: { color: '#ef4444' } },
      { value: 1,  name: '紧急', itemStyle: { color: '#dc2626' } }
    ]
  }]
}

const rogerOption = {
  tooltip: {
    ...TT,
    formatter: (p) => `${p.data[2]}<br/>C₂H₂/C₂H₄=${p.data[0]}<br/>CH₄/H₂=${p.data[1]}`
  },
  grid: { top: 10, bottom: 30, left: 50, right: 10 },
  xAxis: { type: 'value', name: 'C₂H₂/C₂H₄', nameTextStyle: { color: '#9ca3af', fontSize: 10 }, max: 3, ...AXIS },
  yAxis: { type: 'value', name: 'CH₄/H₂',    nameTextStyle: { color: '#9ca3af', fontSize: 10 }, max: 3, ...AXIS },
  series: [{
    type: 'scatter',
    symbolSize: 14,
    data: [
      [0.072, 1.37, '#2主变（低温过热）'],
      [0.02, 0.5, '#1主变（正常）'],
      [0.15, 2.1, '#5主变（中温过热）'],
      [1.8, 0.3, '#7主变（电弧放电）']
    ],
    itemStyle: {
      color: (p) => ['#ef4444', '#10b981', '#f59e0b', '#dc2626'][p.dataIndex],
      shadowBlur: 10,
      shadowColor: '#3b82f6'
    }
  }]
}

const alerts = [
  { level: '紧急', tag: 'tag-red', border: 'border-red-500',    time: '10:42:15', msg: '#2主变 C₂H₂=3.24 ppm 72h 上升 ≥20%',         action: '立即停运，开展油质检测和内部故障排查' },
  { level: '重要', tag: 'tag-org', border: 'border-orange-500', time: '10:15:02', msg: '#2主变 三比值法判定 → 低温过热',             action: '加强气体监测，每天记录 1 次数据，结合油温、局放综合分析' },
  { level: '一般', tag: 'tag-yel', border: 'border-yellow-500', time: '09:30:00', msg: '#2主变 C₂H₄ 72h 上升 23%（趋势异常）',       action: '定期取样检测油质，跟踪气体浓度变化' },
  { level: '提示', tag: 'tag-blu', border: 'border-blue-500',   time: '08:10:20', msg: '智能体已自主优化 C₂H₂ 预警阈值 4.5 ppm',     action: '结合 SFP9-240000/220 型号 + 17 年运行数据' }
]
</script>

<style scoped>
.gas-card {
  background: rgba(31, 41, 55, .5);
  border: 1px solid rgba(75, 85, 99, .4);
  border-radius: 6px;
  padding: 10px;
  position: relative;
  transition: all .3s;
}
.gas-card.warn   { border-color: rgba(245, 158, 11, .5); box-shadow: inset 0 0 12px rgba(245, 158, 11, .1); }
.gas-card.danger { border-color: rgba(239, 68, 68, .6);  box-shadow: inset 0 0 15px rgba(239, 68, 68, .15); }
</style>
