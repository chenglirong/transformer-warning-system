<template>
  <div class="h-screen flex flex-col">
    <AppHeader
      title="机 械 与 结 构 状 态 监 测"
      icon="mdi:vibrate"
      subtitle="维度 3 / 5"
    />

    <section class="px-3 pt-3 grid grid-cols-5 gap-3">
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">振动烈度</p>
            <p class="text-2xl font-bold text-green-400">1.54<span class="text-xs ml-1">mm/s</span></p>
          </div>
          <iconify-icon class="text-3xl text-green-400" icon="mdi:vibrate"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">报警 &gt;2.8 mm/s · 国标</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">运行噪声</p>
            <p class="text-2xl font-bold text-yellow-400">76.3<span class="text-xs ml-1">dB</span></p>
          </div>
          <iconify-icon class="text-3xl text-yellow-400" icon="mdi:volume-high"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">报警 &gt;85 dB @ 1m</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">油枕压力</p>
            <p class="text-2xl font-bold text-green-400">0.08<span class="text-xs ml-1">MPa</span></p>
          </div>
          <iconify-icon class="text-3xl text-green-400" icon="mdi:gauge"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">正常区间 0.02~0.15 MPa</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">油温-环境温差</p>
            <p class="text-2xl font-bold text-yellow-400">21<span class="text-xs ml-1">℃</span></p>
          </div>
          <iconify-icon class="text-3xl text-yellow-400" icon="mdi:thermometer-chevron-up"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">报警 &gt;30℃（正常工况）</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">套管介损 tanδ</p>
            <p class="text-2xl font-bold text-orange-400">0.39<span class="text-xs ml-1">%</span></p>
          </div>
          <iconify-icon class="text-3xl text-orange-400" icon="mdi:transmission-tower-export"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">报警 &gt;0.5%（20℃）</p>
      </KpiCard>
    </section>

    <main class="flex-1 grid grid-cols-12 gap-3 p-3 overflow-hidden" style="min-height: 0">
      <!-- LEFT: vibration + noise -->
      <div class="col-span-5 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 flex-1 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:waveform"></iconify-icon> 振动信号频谱（绕组 + 铁芯）
          </h3>
          <div class="w-full" style="height: calc(100% - 28px)">
            <EChart :option="vibOption" />
          </div>
        </div>
        <div class="glass rounded-lg p-3 flex-1 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:volume-high"></iconify-icon> 噪声分贝 24H 趋势 + 频率分布
          </h3>
          <div class="w-full" style="height: calc(100% - 28px)">
            <EChart :option="noiseOption" />
          </div>
        </div>
      </div>

      <!-- CENTER: oil level + gauge + diff -->
      <div class="col-span-4 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 flex-1 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:oil-level"></iconify-icon> 油位 / 油枕压力
          </h3>
          <div class="grid grid-cols-3 gap-2 items-center" style="height: calc(100% - 28px)">
            <div class="flex flex-col items-center">
              <div class="relative w-16 h-32 bg-gray-800/60 rounded-t-full rounded-b border border-gray-600 overflow-hidden">
                <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-blue-500 to-cyan-400" style="height: 68%"></div>
                <div class="absolute top-0 left-0 right-0 border-b border-dashed border-red-400/60" style="top: 10%"></div>
                <div class="absolute top-0 left-0 right-0 border-b border-dashed border-red-400/60" style="top: 90%"></div>
              </div>
              <p class="text-xs text-gray-400 mt-2">#2 油位</p>
              <p class="text-base font-bold text-green-400">68%</p>
            </div>
            <div class="col-span-2 w-full h-full">
              <EChart :option="gaugeOption" />
            </div>
          </div>
        </div>
        <div class="glass rounded-lg p-3 flex-1 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:thermometer-chevron-up"></iconify-icon> 油温与环境温差 7 日
          </h3>
          <div class="w-full" style="height: calc(100% - 28px)">
            <EChart :option="diffOption" />
          </div>
        </div>
      </div>

      <!-- RIGHT: bushing + alerts -->
      <div class="col-span-3 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:transmission-tower"></iconify-icon> 套管介损 / 泄漏电流
          </h3>
          <div class="space-y-2 text-xs">
            <div
              v-for="b in bushings"
              :key="b.name"
              class="bg-gray-800/60 rounded p-2 border"
              :class="b.borderClass"
            >
              <div class="flex justify-between mb-1">
                <span class="text-gray-400">{{ b.name }}</span>
                <span class="font-bold" :class="b.valueClass">{{ b.value }}</span>
              </div>
              <div class="h-1.5 bg-gray-700 rounded overflow-hidden">
                <div class="h-full" :class="b.barClass" :style="{ width: b.width + '%' }"></div>
              </div>
              <p class="text-[10px] text-gray-500 mt-1">{{ b.hint }}</p>
            </div>
          </div>
        </div>

        <div class="glass rounded-lg p-3 flex-1 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:clipboard-alert"></iconify-icon> 机械/结构预警 &amp; 处置建议
          </h3>
          <div class="space-y-2 overflow-y-auto" style="height: calc(100% - 28px)">
            <div
              v-for="(a, i) in alerts"
              :key="i"
              class="bg-gray-800/40 border-l-4 rounded p-2"
              :class="a.border"
            >
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

const vibOption = {
  tooltip: { trigger: 'axis', ...TT },
  legend: { textStyle: { color: '#9ca3af', fontSize: 10 }, top: 0, right: 0 },
  grid: { top: 25, bottom: 30, left: 40, right: 10 },
  xAxis: {
    type: 'category',
    data: ['50','100','150','200','250','300','400','500','600','800','1k','2k'],
    ...AXIS,
    name: 'Hz',
    nameTextStyle: { color: '#9ca3af' }
  },
  yAxis: { type: 'value', ...AXIS, name: 'mm/s', nameTextStyle: { color: '#9ca3af', fontSize: 10 } },
  series: [
    {
      name: '绕组振动',
      type: 'bar',
      data: [0.8, 1.2, 0.6, 1.54, 0.4, 0.9, 0.3, 0.5, 0.2, 0.3, 0.15, 0.1],
      itemStyle: { color: (p) => (p.value > 2.8 ? '#ef4444' : p.value > 1.4 ? '#f59e0b' : '#3b82f6') }
    },
    {
      name: '铁芯振动',
      type: 'bar',
      data: [0.6, 0.8, 1.1, 1.2, 0.5, 0.3, 0.2, 0.2, 0.1, 0.1, 0.05, 0.05],
      itemStyle: { color: '#06b6d4' }
    },
    {
      name: '阈值',
      type: 'line',
      data: Array(12).fill(2.8),
      lineStyle: { type: 'dashed', color: '#ef4444' },
      symbol: 'none'
    }
  ]
}

const noiseOption = {
  tooltip: { trigger: 'axis', ...TT },
  grid: { top: 25, bottom: 20, left: 35, right: 10 },
  xAxis: { type: 'category', data: ['00', '04', '08', '12', '16', '20', '24'], ...AXIS },
  yAxis: { type: 'value', ...AXIS, name: 'dB', nameTextStyle: { color: '#9ca3af', fontSize: 10 }, max: 100 },
  series: [
    {
      name: '#6主变',
      type: 'line',
      smooth: true,
      data: [74, 73, 76, 80, 82, 79, 76],
      color: '#f59e0b',
      areaStyle: { opacity: 0.15 }
    },
    { name: '#2主变', type: 'line', smooth: true, data: [68, 67, 70, 73, 76, 72, 69], color: '#10b981' },
    {
      name: '报警线',
      type: 'line',
      data: Array(7).fill(85),
      lineStyle: { type: 'dashed', color: '#ef4444' },
      symbol: 'none'
    }
  ]
}

const gaugeOption = {
  series: [
    {
      type: 'gauge',
      center: ['50%', '55%'],
      radius: '82%',
      min: 0,
      max: 0.2,
      splitNumber: 4,
      axisLine: {
        lineStyle: {
          width: 10,
          color: [[0.1, '#ef4444'], [0.4, '#10b981'], [0.75, '#f59e0b'], [1, '#ef4444']]
        }
      },
      pointer: { width: 3, length: '65%', itemStyle: { color: '#06b6d4' } },
      axisTick: { distance: -12, length: 4, lineStyle: { color: '#fff' } },
      splitLine: { distance: -14, length: 8, lineStyle: { color: '#fff' } },
      axisLabel: { color: '#9ca3af', fontSize: 9, distance: -20, formatter: (v) => v.toFixed(2) },
      title: { color: '#9ca3af', fontSize: 10, offsetCenter: [0, '70%'] },
      detail: {
        color: '#10b981',
        fontSize: 16,
        fontWeight: 'bold',
        offsetCenter: [0, '40%'],
        formatter: '{value} MPa'
      },
      data: [{ value: 0.08, name: '油枕压力' }]
    }
  ]
}

const diffOption = {
  tooltip: { trigger: 'axis', ...TT },
  legend: { textStyle: { color: '#9ca3af', fontSize: 10 }, top: 0, right: 0 },
  grid: { top: 25, bottom: 20, left: 35, right: 10 },
  xAxis: { type: 'category', data: ['D-6', 'D-5', 'D-4', 'D-3', 'D-2', 'D-1', '今'], ...AXIS },
  yAxis: { type: 'value', ...AXIS, max: 40 },
  series: [
    {
      name: '#3主变',
      type: 'line',
      smooth: true,
      data: [20, 22, 23, 25, 26, 27, 28],
      color: '#f59e0b',
      areaStyle: { opacity: 0.15 }
    },
    { name: '#1主变', type: 'line', smooth: true, data: [18, 19, 18, 20, 21, 20, 21], color: '#10b981' },
    {
      name: '报警 30℃',
      type: 'line',
      data: Array(7).fill(30),
      lineStyle: { type: 'dashed', color: '#ef4444' },
      symbol: 'none'
    }
  ]
}

const bushings = [
  { name: '#7主变 A 相套管', value: '0.48%', valueClass: 'text-orange-400', borderClass: 'border-orange-500/40', barClass: 'bg-orange-400', width: 96, hint: '泄漏电流 8.2 μA · 趋近阈值' },
  { name: '#7主变 B 相套管', value: '0.42%', valueClass: 'text-yellow-400', borderClass: 'border-yellow-500/40', barClass: 'bg-yellow-400', width: 84, hint: '泄漏电流 6.1 μA' },
  { name: '#7主变 C 相套管', value: '0.31%', valueClass: 'text-green-400', borderClass: 'border-gray-700/60', barClass: 'bg-green-400', width: 62, hint: '泄漏电流 4.3 μA' },
  { name: '#2主变 套管均值', value: '0.28%', valueClass: 'text-green-400', borderClass: 'border-gray-700/60', barClass: 'bg-green-400', width: 56, hint: '泄漏电流 3.8 μA' }
]

const alerts = [
  { level: '重要', tag: 'tag-org', border: 'border-orange-500', time: '08:20:11', msg: '#7主变 A 套管 tanδ=0.48% 趋近 0.5%', action: '停运设备，检修套管，排查受潮、绝缘劣化问题' },
  { level: '一般', tag: 'tag-yel', border: 'border-yellow-500', time: '07:22:10', msg: '#3主变 油温-环境温差 28℃ 持续增大', action: '排查冷却系统故障，清理散热片灰尘，加强环境通风' },
  { level: '一般', tag: 'tag-yel', border: 'border-yellow-500', time: '05:14:30', msg: '#6主变 噪声分贝 82 dB，距阈值 3 dB', action: '现场核查，排查机械松动、铁芯故障，必要时进行降噪处理' },
  { level: '提示', tag: 'tag-blu', border: 'border-blue-500', time: '04:10:00', msg: '#9主变 振动频率峰值偏移 +18%（正常 ±20%）', action: '加强振动监测，排查设备基础松动问题' },
  { level: '提示', tag: 'tag-blu', border: 'border-blue-500', time: '02:45:00', msg: '#4主变 油枕压力波动异常（环境温差联动）', action: '跟踪油位、压力变化，结合环境温度分析' }
]
</script>
