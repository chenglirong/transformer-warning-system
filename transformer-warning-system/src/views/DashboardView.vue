<template>
  <div class="h-screen flex flex-col">
    <AppHeader
      title="变 压 器 智 能 预 警 综 合 大 屏"
      subtitle="接入 128 台 · SCADA 联动"
      :show-back="false"
      large
    />

    <!-- KPI Row -->
    <section class="px-3 pt-3 grid grid-cols-6 gap-3">
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">综合健康度评分</p>
            <p class="text-2xl font-bold text-green-400">92.6<span class="text-xs ml-1">分</span></p>
          </div>
          <iconify-icon class="text-3xl text-green-400" icon="mdi:heart-pulse"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">128 台在运 · 较昨日 <span class="text-green-400">↑ 0.4</span></p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">紧急预警</p>
            <p class="text-2xl font-bold text-red-400">2<span class="text-xs ml-1">条</span></p>
          </div>
          <iconify-icon class="text-3xl text-red-400 pulse" icon="mdi:alert-octagon"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">C₂H₂ / 温度超标 → 立即停运</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">重要预警</p>
            <p class="text-2xl font-bold text-orange-400">5<span class="text-xs ml-1">条</span></p>
          </div>
          <iconify-icon class="text-3xl text-orange-400" icon="mdi:alert"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">过载 / 局放 / 套管介损</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">一般预警</p>
            <p class="text-2xl font-bold text-yellow-400">9<span class="text-xs ml-1">条</span></p>
          </div>
          <iconify-icon class="text-3xl text-yellow-400" icon="mdi:information"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">趋势异常 / 电压越限</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">提示类</p>
            <p class="text-2xl font-bold text-blue-400">4<span class="text-xs ml-1">条</span></p>
          </div>
          <iconify-icon class="text-3xl text-blue-400" icon="mdi:bell-outline"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">极端环境 / 波动监测</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">智能体阈值优化</p>
            <p class="text-2xl font-bold text-purple-400">37<span class="text-xs ml-1">项</span></p>
          </div>
          <iconify-icon class="text-3xl text-purple-400" icon="mdi:robot"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">近 7 日自学习优化数</p>
      </KpiCard>
    </section>

    <main class="flex-1 grid grid-cols-12 gap-3 p-3 overflow-hidden" style="min-height: 0">
      <!-- LEFT: 电气性能 + 机械与结构 -->
      <div class="col-span-3 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 flex-1 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between">
            <span class="flex items-center gap-2">
              <iconify-icon icon="mdi:lightning-bolt"></iconify-icon> 电气性能类
            </span>
            <RouterLink to="/load-warning" class="text-[10px] text-gray-500 hover:text-cyan-400">详情 →</RouterLink>
          </h3>
          <div class="space-y-1.5 text-xs">
            <MetricRow v-for="m in electricalMetrics" :key="m.label" v-bind="m" />
          </div>
        </div>

        <div class="glass rounded-lg p-3 flex-1 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between">
            <span class="flex items-center gap-2">
              <iconify-icon icon="mdi:vibrate"></iconify-icon> 机械与结构状态
            </span>
            <RouterLink to="/mechanical-structure" class="text-[10px] text-gray-500 hover:text-cyan-400">详情 →</RouterLink>
          </h3>
          <div class="space-y-1.5 text-xs">
            <MetricRow v-for="m in mechanicalMetrics" :key="m.label" v-bind="m" />
          </div>
        </div>
      </div>

      <!-- CENTER: DGA + radar + trend -->
      <div class="col-span-6 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 1.4">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between">
            <span class="flex items-center gap-2">
              <iconify-icon icon="mdi:test-tube"></iconify-icon> 油中溶解气体 DGA 分析
            </span>
            <span class="flex items-center gap-2 text-[10px]">
              <span class="text-gray-500">
                三比值法：<span class="text-orange-400">潜在低温过热 (&lt;300℃)</span>
              </span>
              <RouterLink to="/insulation-performance" class="text-gray-500 hover:text-cyan-400">详情 →</RouterLink>
            </span>
          </h3>
          <div class="grid grid-cols-7 gap-2 mb-2">
            <div
              v-for="g in gases"
              :key="g.sym"
              class="bg-gray-800/50 rounded p-2 text-center"
              :class="g.border"
            >
              <p class="text-[10px] text-gray-400">{{ g.sym }}<span v-if="g.warn"> ⚠</span></p>
              <p class="text-base font-bold" :class="g.color">{{ g.value }}</p>
              <p class="text-[10px] text-gray-500">{{ g.unit }}</p>
            </div>
          </div>
          <div class="w-full" style="height: calc(100% - 100px)">
            <EChart :option="dgaOption" />
          </div>
        </div>

        <!-- radar + 24H trend -->
        <div class="flex-1 grid grid-cols-2 gap-3 overflow-hidden">
          <div class="glass rounded-lg p-3 overflow-hidden">
            <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
              <iconify-icon icon="mdi:radar"></iconify-icon> 五大维度健康度雷达
            </h3>
            <div class="w-full" style="height: calc(100% - 28px)">
              <EChart :option="radarOption" />
            </div>
          </div>
          <div class="glass rounded-lg p-3 overflow-hidden">
            <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
              <iconify-icon icon="mdi:chart-bell-curve"></iconify-icon> 24H 预警等级分布趋势
            </h3>
            <div class="w-full" style="height: calc(100% - 28px)">
              <EChart :option="trendOption" />
            </div>
          </div>
        </div>
      </div>

      <!-- RIGHT: auxiliary / environment / marquee -->
      <div class="col-span-3 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between">
            <span class="flex items-center gap-2">
              <iconify-icon icon="mdi:fan"></iconify-icon> 冷却与辅助系统
            </span>
            <RouterLink to="/auxiliary-system" class="text-[10px] text-gray-500 hover:text-cyan-400">详情 →</RouterLink>
          </h3>
          <div class="grid grid-cols-4 gap-2 text-center">
            <div class="bg-gray-800/50 rounded p-2 border border-green-500/30">
              <iconify-icon class="text-2xl text-green-400" icon="mdi:fan"></iconify-icon>
              <p class="text-[10px] text-gray-400 mt-1">风机组</p>
              <p class="text-xs font-bold text-green-400">4/4</p>
            </div>
            <div class="bg-gray-800/50 rounded p-2 border border-yellow-500/40">
              <iconify-icon class="text-2xl text-yellow-400" icon="mdi:pump"></iconify-icon>
              <p class="text-[10px] text-gray-400 mt-1">油泵</p>
              <p class="text-xs font-bold text-yellow-400">3/4</p>
            </div>
            <div class="bg-gray-800/50 rounded p-2 border border-green-500/30">
              <iconify-icon class="text-2xl text-green-400" icon="mdi:thermometer-lines"></iconify-icon>
              <p class="text-[10px] text-gray-400 mt-1">进出温差</p>
              <p class="text-xs font-bold text-green-400">8.2℃</p>
            </div>
            <div class="bg-gray-800/50 rounded p-2 border border-green-500/30">
              <iconify-icon class="text-2xl text-green-400" icon="mdi:power-plug"></iconify-icon>
              <p class="text-[10px] text-gray-400 mt-1">控制电源</p>
              <p class="text-xs font-bold text-green-400">正常</p>
            </div>
          </div>
        </div>

        <div class="glass rounded-lg p-3 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between">
            <span class="flex items-center gap-2">
              <iconify-icon icon="mdi:weather-partly-cloudy"></iconify-icon> 环境与工况
            </span>
            <RouterLink to="/environment-monitoring" class="text-[10px] text-gray-500 hover:text-cyan-400">详情 →</RouterLink>
          </h3>
          <div class="grid grid-cols-4 gap-2 text-center">
            <div class="bg-gray-800/50 rounded p-2 border border-yellow-500/30">
              <iconify-icon class="text-2xl text-yellow-400" icon="mdi:thermometer"></iconify-icon>
              <p class="text-[10px] text-gray-400 mt-1">环境温度</p>
              <p class="text-xs font-bold text-yellow-400">38℃</p>
            </div>
            <div class="bg-gray-800/50 rounded p-2 border border-green-500/30">
              <iconify-icon class="text-2xl text-green-400" icon="mdi:water-percent"></iconify-icon>
              <p class="text-[10px] text-gray-400 mt-1">湿度</p>
              <p class="text-xs font-bold text-green-400">62%</p>
            </div>
            <div class="bg-gray-800/50 rounded p-2 border border-green-500/30">
              <iconify-icon class="text-2xl text-green-400" icon="mdi:cctv"></iconify-icon>
              <p class="text-[10px] text-gray-400 mt-1">异物入侵</p>
              <p class="text-xs font-bold text-green-400">无</p>
            </div>
            <div class="bg-gray-800/50 rounded p-2 border border-green-500/30">
              <iconify-icon class="text-2xl text-green-400" icon="mdi:weather-fog"></iconify-icon>
              <p class="text-[10px] text-gray-400 mt-1">凝露</p>
              <p class="text-xs font-bold text-green-400">无</p>
            </div>
          </div>
        </div>

        <!-- Marquee alerts -->
        <div class="glass rounded-lg p-3 flex-1 overflow-hidden marquee-wrap">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between">
            <span><iconify-icon icon="mdi:bell-ring"></iconify-icon> 实时预警与智能体处置建议</span>
            <RouterLink to="/alert-management" class="text-[10px] text-gray-500 hover:text-cyan-400">管理 →</RouterLink>
          </h3>
          <div class="overflow-hidden" style="height: calc(100% - 28px)">
            <div class="marquee space-y-2">
              <div
                v-for="(a, i) in marqueeAlerts"
                :key="i"
                class="bg-gray-800/40 border-l-4 rounded p-2"
                :class="a.border"
              >
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
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import KpiCard from '@/components/KpiCard.vue'
import MetricRow from '@/components/MetricRow.vue'
import EChart from '@/components/EChart.vue'
import { AXIS, TT } from '@/utils/chartDefaults'

const electricalMetrics = [
  { label: '绕组温度',     value: '82℃',    suffix: '/105',  width: 78, barClass: 'bg-yellow-400', valueClass: 'text-yellow-400' },
  { label: '顶层油温',     value: '59℃',    suffix: '/95',   width: 62, barClass: 'bg-green-400',  valueClass: 'text-green-400' },
  { label: '负载电流',     value: '1.05倍',  suffix: '/1.1',  width: 92, barClass: 'bg-orange-400', valueClass: 'text-orange-400' },
  { label: '三相不平衡度', value: '3.8%',   suffix: '/10',   width: 38, barClass: 'bg-green-400',  valueClass: 'text-green-400' },
  { label: '局部放电量',   value: '88pC',   suffix: '/100',  width: 88, barClass: 'bg-red-400',    valueClass: 'text-red-400' },
  { label: '铁芯接地电流', value: '35mA',   suffix: '/100',  width: 35, barClass: 'bg-green-400',  valueClass: 'text-green-400' },
  { label: '运行电压偏差', value: '+2.1%',  suffix: '/±5',   width: 42, barClass: 'bg-green-400',  valueClass: 'text-green-400' },
  { label: '分接档位切换', value: '12次/日', suffix: '/20',   width: 55, barClass: 'bg-yellow-400', valueClass: 'text-yellow-400' }
]

const mechanicalMetrics = [
  { label: '振动烈度',     value: '1.54',  suffix: 'mm/s',    width: 55, barClass: 'bg-green-400',  valueClass: 'text-green-400' },
  { label: '运行噪声',     value: '76.3',  suffix: 'dB / 85', width: 72, barClass: 'bg-yellow-400', valueClass: 'text-yellow-400' },
  { label: '油位（相对）', value: '68%',   suffix: '正常',     width: 68, barClass: 'bg-green-400',  valueClass: 'text-green-400' },
  { label: '油枕压力',     value: '0.08',  suffix: 'MPa',     width: 50, barClass: 'bg-green-400',  valueClass: 'text-green-400' },
  { label: '油温环境温差', value: '21℃',   suffix: '/30',     width: 70, barClass: 'bg-yellow-400', valueClass: 'text-yellow-400' },
  { label: '套管介损 tanδ',value: '0.39%', suffix: '/0.5',    width: 78, barClass: 'bg-orange-400', valueClass: 'text-orange-400' },
  { label: '套管泄漏电流', value: '5.2',   suffix: 'μA / 10', width: 52, barClass: 'bg-green-400',  valueClass: 'text-green-400' }
]

const gases = [
  { sym: 'H₂',   value: '42.5', unit: '/150 ppm', color: 'text-green-400',  border: 'border border-gray-700/50',  warn: false },
  { sym: 'CH₄',  value: '58.2', unit: 'ppm',      color: 'text-green-400',  border: 'border border-gray-700/50',  warn: false },
  { sym: 'C₂H₆', value: '22.8', unit: 'ppm',      color: 'text-green-400',  border: 'border border-gray-700/50',  warn: false },
  { sym: 'C₂H₄', value: '45.1', unit: 'ppm',      color: 'text-yellow-400', border: 'border border-yellow-500/40', warn: false },
  { sym: 'C₂H₂', value: '3.24', unit: '/5 ppm',   color: 'text-red-400',    border: 'border border-red-500/50',    warn: true  },
  { sym: 'CO',   value: '312',  unit: 'ppm',      color: 'text-green-400',  border: 'border border-gray-700/50',  warn: false },
  { sym: 'CO₂',  value: '1840', unit: 'ppm',      color: 'text-green-400',  border: 'border border-gray-700/50',  warn: false }
]

const dgaOption = {
  tooltip: { trigger: 'axis', ...TT },
  legend: { textStyle: { color: '#9ca3af', fontSize: 10 }, top: 0, right: 0, itemWidth: 10, itemHeight: 6 },
  grid: { top: 50, bottom: 20, left: 40, right: 70 },
  xAxis: { type: 'category', data: ['D-6', 'D-5', 'D-4', 'D-3', 'D-2', 'D-1', '今日'], ...AXIS },
  yAxis: [
    { type: 'value', name: 'ppm',  nameTextStyle: { color: '#9ca3af', fontSize: 10 }, ...AXIS },
    { type: 'value', name: 'C₂H₂', nameTextStyle: { color: '#ef4444', fontSize: 10 }, ...AXIS, max: 5 }
  ],
  series: [
    { name: 'H₂',   type: 'line', smooth: true, data: [28, 32, 35, 38, 40, 41, 42.5],  color: '#10b981' },
    { name: 'CH₄',  type: 'line', smooth: true, data: [42, 45, 48, 52, 55, 57, 58.2],  color: '#06b6d4' },
    { name: 'C₂H₆', type: 'line', smooth: true, data: [18, 19, 20, 21, 22, 22.5, 22.8], color: '#8b5cf6' },
    { name: 'C₂H₄', type: 'line', smooth: true, data: [30, 32, 36, 40, 42, 44, 45.1],  color: '#f59e0b' },
    {
      name: 'C₂H₂（右轴）',
      type: 'line',
      smooth: true,
      yAxisIndex: 1,
      data: [1.1, 1.4, 1.8, 2.2, 2.6, 2.9, 3.24],
      color: '#ef4444',
      lineStyle: { width: 2.5 },
      markLine: {
        symbol: 'none',
        data: [{
          yAxis: 5,
          lineStyle: { color: '#dc2626', type: 'dashed' },
          label: { formatter: '报警阈值 5ppm', color: '#fca5a5', fontSize: 10 }
        }]
      }
    }
  ]
}

const radarOption = {
  tooltip: { ...TT },
  legend: { textStyle: { color: '#9ca3af', fontSize: 10 }, top: 0, right: 0 },
  radar: {
    indicator: [
      { name: '电气性能', max: 100 },
      { name: 'DGA油气', max: 100 },
      { name: '机械结构', max: 100 },
      { name: '冷却辅助', max: 100 },
      { name: '环境工况', max: 100 }
    ],
    center: ['50%', '55%'],
    radius: '62%',
    axisName: { color: '#cbd5e1', fontSize: 10 },
    splitLine: { lineStyle: { color: 'rgba(59,130,246,.2)' } },
    splitArea: { areaStyle: { color: ['rgba(59,130,246,.02)', 'rgba(59,130,246,.06)'] } },
    axisLine: { lineStyle: { color: 'rgba(59,130,246,.2)' } }
  },
  series: [{
    type: 'radar',
    data: [
      {
        value: [82, 74, 88, 91, 85],
        name: '当前状态',
        areaStyle: { color: 'rgba(59,130,246,.3)' },
        lineStyle: { color: '#3b82f6' },
        itemStyle: { color: '#3b82f6' }
      },
      {
        value: [85, 85, 85, 85, 85],
        name: '预警阈值',
        areaStyle: { color: 'rgba(239,68,68,.08)' },
        lineStyle: { type: 'dashed', color: '#ef4444' },
        itemStyle: { color: '#ef4444' }
      }
    ]
  }]
}

const trendOption = {
  tooltip: { trigger: 'axis', ...TT },
  legend: { textStyle: { color: '#9ca3af', fontSize: 10 }, top: 0, right: 0, itemWidth: 10, itemHeight: 6 },
  grid: { top: 25, bottom: 20, left: 30, right: 10 },
  xAxis: {
    type: 'category',
    data: ['0', '2', '4', '6', '8', '10', '12', '14', '16', '18', '20', '22'],
    ...AXIS
  },
  yAxis: { type: 'value', ...AXIS },
  series: [
    { name: '紧急', type: 'bar', stack: 'x', data: [0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0], itemStyle: { color: '#ef4444' } },
    { name: '重要', type: 'bar', stack: 'x', data: [1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0], itemStyle: { color: '#f97316' } },
    { name: '一般', type: 'bar', stack: 'x', data: [2, 1, 2, 1, 3, 2, 3, 2, 2, 1, 2, 1], itemStyle: { color: '#f59e0b' } },
    { name: '提示', type: 'bar', stack: 'x', data: [1, 1, 2, 2, 2, 1, 2, 1, 1, 2, 1, 1], itemStyle: { color: '#3b82f6' } }
  ]
}

const baseAlerts = [
  { level: '紧急', tag: 'tag-red', border: 'border-red-500',    time: '10:42:15', msg: '#2主变 C₂H₂=3.24ppm 72h上升 ≥20%',       action: '处置：立即停运，开展油质检测与内部故障排查' },
  { level: '重要', tag: 'tag-org', border: 'border-orange-500', time: '10:15:02', msg: '#2主变 局放量 88pC 趋近 100pC 阈值',     action: '处置：停运设备，开展局放定位检测，排查绝缘缺陷' },
  { level: '紧急', tag: 'tag-red', border: 'border-red-500',    time: '09:58:30', msg: '#5主变 绕组温度 102℃ 逼近 105℃',         action: '处置：立即检查冷却系统，降低负载，若持续升高则停运' },
  { level: '重要', tag: 'tag-org', border: 'border-orange-500', time: '09:15:30', msg: '#1主变 冷却油泵 1 台停机（4 组→3 组）',  action: '处置：立即检修故障油泵，冷却失效则停运变压器' },
  { level: '一般', tag: 'tag-yel', border: 'border-yellow-500', time: '08:50:44', msg: '#5主变 负载电流 1.05 倍额定（长期）',    action: '处置：调整负载分配，降低过载电流，监测绕组温度' },
  { level: '重要', tag: 'tag-org', border: 'border-orange-500', time: '08:20:11', msg: '#7主变 套管介损 tanδ=0.48% 逼近 0.5%',   action: '处置：停运检修套管，排查受潮与绝缘劣化' },
  { level: '一般', tag: 'tag-yel', border: 'border-yellow-500', time: '07:22:10', msg: '#3主变 油温-环境温差 28℃ 持续增大',     action: '处置：排查冷却系统，清理散热片灰尘，加强通风' },
  { level: '提示', tag: 'tag-blu', border: 'border-blue-500',   time: '06:45:20', msg: '环境温度 38℃ 接近 40℃ 阈值',            action: '处置：智能体联动下调本体温度预警阈值 5%' },
  { level: '一般', tag: 'tag-yel', border: 'border-yellow-500', time: '05:30:12', msg: '#4主变 分接开关 12 次/日 高于历史均值', action: '处置：核查电压波动，稳定运行电压，监测控制回路' },
  { level: '提示', tag: 'tag-blu', border: 'border-blue-500',   time: '04:10:00', msg: '#9主变 振动频率峰值偏移 +18%',          action: '处置：加强振动监测，排查设备基础松动' }
]

// Double the list for seamless vertical marquee
const marqueeAlerts = computed(() => [...baseAlerts, ...baseAlerts])
</script>
