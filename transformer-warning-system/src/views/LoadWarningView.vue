<template>
  <div class="h-screen flex flex-col">
    <AppHeader
      title="电 气 性 能 监 测（核 心 监 控）"
      icon="mdi:lightning-bolt"
      subtitle="维度 1 / 5"
    />

    <section class="px-3 pt-3 grid grid-cols-5 gap-3">
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">绕组温度 峰值</p>
            <p class="text-2xl font-bold text-yellow-400">82<span class="text-xs ml-1">℃</span></p>
          </div>
          <iconify-icon class="text-3xl text-yellow-400" icon="mdi:thermometer-high"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">报警 &gt;105℃ · 预警 24h ≥10℃</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">顶层油温 峰值</p>
            <p class="text-2xl font-bold text-green-400">59<span class="text-xs ml-1">℃</span></p>
          </div>
          <iconify-icon class="text-3xl text-green-400" icon="mdi:thermometer-lines"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">报警 &gt;95℃ · 环境 +32℃</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">最大负载率</p>
            <p class="text-2xl font-bold text-orange-400">1.05<span class="text-xs ml-1">倍</span></p>
          </div>
          <iconify-icon class="text-3xl text-orange-400" icon="mdi:gauge"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">报警 &gt;1.1 倍额定 · 长期运行</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">最大局放量</p>
            <p class="text-2xl font-bold text-red-400">88<span class="text-xs ml-1">pC</span></p>
          </div>
          <iconify-icon class="text-3xl text-red-400 pulse" icon="mdi:flash-alert"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">报警 &gt;100pC · 油浸式变压器</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">铁芯接地电流</p>
            <p class="text-2xl font-bold text-green-400">35<span class="text-xs ml-1">mA</span></p>
          </div>
          <iconify-icon class="text-3xl text-green-400" icon="mdi:earth"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">报警 &gt;100mA · 多点接地</p>
      </KpiCard>
    </section>

    <main class="flex-1 grid grid-cols-12 gap-3 p-3 overflow-hidden" style="min-height: 0">
      <div class="col-span-8 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 flex-1 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:chart-line"></iconify-icon> 绕组温度 / 顶层油温 / 环境温度 趋势（24H）
          </h3>
          <div class="w-full" style="height: calc(100% - 28px)">
            <EChart :option="tempOption" />
          </div>
        </div>
        <div class="flex-1 grid grid-cols-2 gap-3 overflow-hidden">
          <div class="glass rounded-lg p-3 overflow-hidden">
            <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
              <iconify-icon icon="mdi:transmission-tower"></iconify-icon> 负载率趋势（阈值 110%）
            </h3>
            <div class="w-full" style="height: calc(100% - 28px)">
              <EChart :option="loadOption" />
            </div>
          </div>
          <div class="glass rounded-lg p-3 overflow-hidden">
            <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
              <iconify-icon icon="mdi:scale-balance"></iconify-icon> 三相不平衡度（阈值 10%）
            </h3>
            <div class="w-full" style="height: calc(100% - 28px)">
              <EChart :option="balanceOption" />
            </div>
          </div>
        </div>
        <div class="flex-1 grid grid-cols-2 gap-3 overflow-hidden">
          <div class="glass rounded-lg p-3 overflow-hidden">
            <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
              <iconify-icon icon="mdi:flash-alert-outline"></iconify-icon> 局部放电量 7 日趋势（pC）
            </h3>
            <div class="w-full" style="height: calc(100% - 28px)">
              <EChart :option="pdOption" />
            </div>
          </div>
          <div class="glass rounded-lg p-3 overflow-hidden">
            <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
              <iconify-icon icon="mdi:earth"></iconify-icon> 铁芯接地电流 7 日（mA）
            </h3>
            <div class="w-full" style="height: calc(100% - 28px)">
              <EChart :option="groundOption" />
            </div>
          </div>
        </div>
      </div>

      <div class="col-span-4 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:sine-wave"></iconify-icon> 三相运行电压（阈值 ±5%）
          </h3>
          <div class="grid grid-cols-3 gap-2 text-xs">
            <div v-for="p in phases" :key="p.name" class="bg-gray-800/60 rounded p-2 border border-gray-700/60 text-center">
              <p class="text-[10px] text-gray-400">{{ p.name }}</p>
              <p class="text-lg font-bold text-green-400">{{ p.kv }}<span class="text-[10px]">kV</span></p>
              <p class="text-[10px] text-gray-500">{{ p.dev }}</p>
            </div>
          </div>
        </div>

        <div class="glass rounded-lg p-3 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:knob"></iconify-icon> 有载分接开关
          </h3>
          <div class="grid grid-cols-2 gap-2 text-xs">
            <div class="bg-gray-800/60 rounded p-2 border border-yellow-500/30">
              <p class="text-[10px] text-gray-400">当前档位</p>
              <p class="text-base font-bold text-yellow-400">9 / 17</p>
              <p class="text-[10px] text-gray-500">今日切换 12 次</p>
            </div>
            <div class="bg-gray-800/60 rounded p-2 border border-gray-700/60">
              <p class="text-[10px] text-gray-400">切换累计</p>
              <p class="text-base font-bold text-cyan-400">28,462 次</p>
              <p class="text-[10px] text-gray-500">设计 60,000 次</p>
            </div>
          </div>
          <p class="text-[10px] text-gray-500 mt-2">智能体学习：正常切换频率 3~8 次/日，当前偏高 → 一般预警</p>
        </div>

        <div class="glass rounded-lg p-3 flex-1 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:link-variant"></iconify-icon> 电气关联预警 &amp; 处置建议
          </h3>
          <div class="space-y-2 overflow-y-auto" style="height: calc(100% - 28px)">
            <div v-for="(a, i) in alerts" :key="i" class="bg-gray-800/40 border-l-4 rounded p-2" :class="a.border">
              <div class="flex justify-between items-center mb-1">
                <span class="text-[10px] px-1.5 py-0.5 rounded" :class="a.tag">【{{ a.level }}】</span>
                <span class="text-[10px] text-gray-500">{{ a.time }}</span>
              </div>
              <p class="text-xs text-gray-100">{{ a.msg }}</p>
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

const phases = [
  { name: 'A 相', kv: '227.3', dev: '+1.0%' },
  { name: 'B 相', kv: '229.1', dev: '+1.8%' },
  { name: 'C 相', kv: '226.5', dev: '+0.7%' }
]

const tempOption = {
  tooltip: { trigger: 'axis', ...TT },
  legend: { textStyle: { color: '#9ca3af', fontSize: 10 }, top: 0, right: 0 },
  grid: { top: 25, bottom: 20, left: 35, right: 10 },
  xAxis: {
    type: 'category',
    data: ['00', '02', '04', '06', '08', '10', '12', '14', '16', '18', '20', '22', '24'],
    ...AXIS
  },
  yAxis: { type: 'value', ...AXIS, max: 120, name: '℃', nameTextStyle: { color: '#9ca3af', fontSize: 10 } },
  series: [
    { name: '绕组温度', type: 'line', smooth: true, data: [62,58,55,58,65,72,78,80,82,81,76,70,65], color: '#f59e0b', areaStyle: { opacity: 0.15 } },
    { name: '顶层油温', type: 'line', smooth: true, data: [45,42,40,42,48,52,56,58,59,58,55,50,46], color: '#10b981' },
    { name: '环境温度', type: 'line', smooth: true, data: [26,24,22,24,28,31,34,36,38,37,33,29,27], color: '#06b6d4' },
    { name: '绕组报警', type: 'line', data: Array(13).fill(105), lineStyle: { type: 'dashed', color: '#ef4444' }, symbol: 'none' },
    { name: '油温报警', type: 'line', data: Array(13).fill(95),  lineStyle: { type: 'dashed', color: '#f97316' }, symbol: 'none' }
  ]
}

const loadOption = {
  tooltip: { trigger: 'axis', ...TT },
  legend: { textStyle: { color: '#9ca3af', fontSize: 10 }, top: 0, right: 0 },
  grid: { top: 25, bottom: 20, left: 35, right: 10 },
  xAxis: { type: 'category', data: ['00', '04', '08', '12', '16', '20', '24'], ...AXIS },
  yAxis: { type: 'value', max: 120, ...AXIS, axisLabel: { ...AXIS.axisLabel, formatter: '{value}%' } },
  series: [
    { name: '#1主变', type: 'line', smooth: true, data: [42, 38, 55, 72, 78, 68, 55], color: '#3b82f6' },
    { name: '#2主变', type: 'line', smooth: true, data: [50, 45, 60, 82, 89, 76, 62], color: '#ef4444' },
    { name: '#5主变', type: 'line', smooth: true, data: [48, 44, 58, 79, 105, 87, 68], color: '#f59e0b', areaStyle: { opacity: 0.15 } },
    { name: '阈值', type: 'line', data: Array(7).fill(110), lineStyle: { type: 'dashed', color: '#dc2626' }, symbol: 'none' }
  ]
}

const balanceOption = {
  tooltip: { trigger: 'axis', ...TT },
  grid: { top: 25, bottom: 20, left: 30, right: 10 },
  xAxis: { type: 'category', data: ['#1', '#2', '#3', '#4', '#5', '#6', '#7', '#8'], ...AXIS },
  yAxis: { type: 'value', ...AXIS, axisLabel: { ...AXIS.axisLabel, formatter: '{value}%' }, max: 15 },
  series: [
    {
      name: '不平衡度',
      type: 'bar',
      data: [3.8, 5.2, 4.1, 2.9, 8.4, 3.1, 6.8, 2.5],
      itemStyle: { color: (p) => (p.value > 10 ? '#ef4444' : p.value > 7 ? '#f59e0b' : '#10b981') },
      markLine: {
        symbol: 'none',
        data: [{
          yAxis: 10,
          lineStyle: { color: '#ef4444', type: 'dashed' },
          label: { color: '#fca5a5', fontSize: 10, formatter: '阈值 10%' }
        }]
      }
    }
  ]
}

const pdOption = {
  tooltip: { trigger: 'axis', ...TT },
  grid: { top: 20, bottom: 20, left: 30, right: 10 },
  xAxis: { type: 'category', data: ['D-6', 'D-5', 'D-4', 'D-3', 'D-2', 'D-1', '今'], ...AXIS },
  yAxis: { type: 'value', ...AXIS, max: 150 },
  series: [
    {
      name: '#2主变',
      type: 'line',
      smooth: true,
      data: [35, 42, 55, 63, 72, 81, 88],
      color: '#ef4444',
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(239,68,68,.4)' },
            { offset: 1, color: 'rgba(239,68,68,0)' }
          ]
        }
      },
      markLine: {
        symbol: 'none',
        data: [{
          yAxis: 100,
          lineStyle: { color: '#dc2626', type: 'dashed' },
          label: { color: '#fca5a5', fontSize: 10, formatter: '报警 100pC' }
        }]
      }
    }
  ]
}

const groundOption = {
  tooltip: { trigger: 'axis', ...TT },
  legend: { textStyle: { color: '#9ca3af', fontSize: 10 }, top: 0, right: 0 },
  grid: { top: 25, bottom: 20, left: 30, right: 10 },
  xAxis: { type: 'category', data: ['D-6', 'D-5', 'D-4', 'D-3', 'D-2', 'D-1', '今'], ...AXIS },
  yAxis: { type: 'value', ...AXIS, max: 120 },
  series: [
    { name: '#1', type: 'bar', data: [18, 19, 22, 20, 24, 23, 25], itemStyle: { color: '#10b981' } },
    { name: '#2', type: 'bar', data: [28, 32, 35, 31, 29, 34, 35], itemStyle: { color: '#f59e0b' } },
    { name: '#5', type: 'bar', data: [15, 16, 18, 17, 16, 18, 19], itemStyle: { color: '#3b82f6' } },
    { name: '报警线', type: 'line', data: Array(7).fill(100), lineStyle: { type: 'dashed', color: '#ef4444' }, symbol: 'none' }
  ]
}

const alerts = [
  { level: '紧急', tag: 'tag-red', border: 'border-red-500',    time: '10:42:15', msg: '#5主变 油温升高 + 负载电流超标（关联预警）',       action: '立即检查冷却系统，降低负载，若温度持续升高则停运' },
  { level: '重要', tag: 'tag-org', border: 'border-orange-500', time: '10:15:02', msg: '#2主变 局放量 88pC 趋近阈值（关联 DGA C₂H₂ 异常）', action: '停运设备，开展局放定位检测，排查绝缘缺陷' },
  { level: '一般', tag: 'tag-yel', border: 'border-yellow-500', time: '08:50:44', msg: '#5主变 负载电流 1.05 倍额定（长期）',                action: '调整负载分配，降低过载电流，监测绕组温度' },
  { level: '一般', tag: 'tag-yel', border: 'border-yellow-500', time: '07:12:19', msg: '#4主变 分接开关 12 次/日 高于历史均值',              action: '核查电压波动，稳定运行电压，监测控制回路' },
  { level: '提示', tag: 'tag-blu', border: 'border-blue-500',   time: '06:30:00', msg: '#8主变 铁芯接地电流波动幅度异常',                  action: '定期监测电流变化，检查接地回路' }
]
</script>
