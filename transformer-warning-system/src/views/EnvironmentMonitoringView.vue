<template>
  <div class="h-screen flex flex-col">
    <AppHeader
      title="环 境 与 工 况 监 测"
      icon="mdi:weather-partly-cloudy"
      subtitle="维度 5 / 5"
    />

    <section class="px-3 pt-3 grid grid-cols-5 gap-3">
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">环境温度</p>
            <p class="text-2xl font-bold text-yellow-400">38<span class="text-xs ml-1">℃</span></p>
          </div>
          <iconify-icon class="text-3xl text-yellow-400" icon="mdi:thermometer"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">报警 &gt;40℃ / &lt;-20℃</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">环境湿度</p>
            <p class="text-2xl font-bold text-green-400">62<span class="text-xs ml-1">%</span></p>
          </div>
          <iconify-icon class="text-3xl text-green-400" icon="mdi:water-percent"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">报警 &gt;85%（凝露）</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">异物入侵</p>
            <p class="text-2xl font-bold text-green-400">0<span class="text-xs ml-1">起</span></p>
          </div>
          <iconify-icon class="text-3xl text-green-400" icon="mdi:cctv"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">视频 AI 24H 无异常</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">凝露状态</p>
            <p class="text-2xl font-bold text-green-400">无</p>
          </div>
          <iconify-icon class="text-3xl text-green-400" icon="mdi:weather-fog"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">露点温度 27℃ · 差值 11℃</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">智能体阈值联动</p>
            <p class="text-2xl font-bold text-purple-400">已下调<span class="text-xs ml-1">5%</span></p>
          </div>
          <iconify-icon class="text-3xl text-purple-400" icon="mdi:robot"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">高温工况 → 下调温度预警线</p>
      </KpiCard>
    </section>

    <main class="flex-1 grid grid-cols-12 gap-3 p-3 overflow-hidden" style="min-height: 0">
      <!-- LEFT: temp / humidity trends -->
      <div class="col-span-5 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 flex-1 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:chart-multiline"></iconify-icon> 环境温度 / 湿度 24H 趋势
          </h3>
          <div class="w-full" style="height: calc(100% - 28px)">
            <EChart :option="envOption" />
          </div>
        </div>
        <div class="glass rounded-lg p-3 flex-1 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:chart-bar"></iconify-icon> 各变电站环境差异对比
          </h3>
          <div class="w-full" style="height: calc(100% - 28px)">
            <EChart :option="siteOption" />
          </div>
        </div>
      </div>

      <!-- CENTER: cctv + dew -->
      <div class="col-span-4 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 flex-1 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between">
            <span><iconify-icon icon="mdi:cctv"></iconify-icon> 视频监控 · 异物入侵 AI 识别</span>
            <span class="flex items-center gap-1 text-[10px] text-red-400">
              <span class="live-dot"></span> LIVE · 4 路
            </span>
          </h3>
          <div class="grid grid-cols-2 gap-2" style="height: calc(100% - 28px)">
            <div v-for="(c, i) in cams" :key="i" class="cctv-mock rounded flex flex-col relative">
              <div class="flex-1 flex items-center justify-center text-gray-600">
                <iconify-icon class="text-4xl" icon="mdi:video"></iconify-icon>
              </div>
              <div class="absolute top-1 left-1 text-[10px] text-green-400">{{ c.name }}</div>
              <div class="absolute bottom-1 right-1 text-[10px] text-gray-500">正常</div>
              <div
                v-if="c.box"
                class="absolute w-16 h-10 border-2 border-green-400 rounded"
                style="top: 2rem; left: 1.5rem"
              ></div>
            </div>
          </div>
        </div>
        <div class="glass rounded-lg p-3 flex-1 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:weather-fog"></iconify-icon> 凝露风险评估（温度 vs 露点）
          </h3>
          <div class="w-full" style="height: calc(100% - 28px)">
            <EChart :option="dewOption" />
          </div>
        </div>
      </div>

      <!-- RIGHT: adaptation + alerts -->
      <div class="col-span-3 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:robot"></iconify-icon> 智能体工况适配
          </h3>
          <div class="space-y-2 text-xs">
            <div class="bg-purple-500/10 border border-purple-500/30 rounded p-2">
              <p class="text-purple-300 font-bold text-[11px] flex items-center gap-1">
                <iconify-icon icon="mdi:auto-fix"></iconify-icon> 联动调整（最近 1h）
              </p>
              <ul class="text-[10px] text-gray-400 mt-1 space-y-0.5">
                <li>• 油温报警阈值 95℃ → <span class="text-cyan-400">90℃</span>（环境 38℃）</li>
                <li>• 油枕压力上限 0.15 → <span class="text-cyan-400">0.14 MPa</span></li>
                <li>• 冷却效率基线 93.8% → <span class="text-cyan-400">94.5%</span></li>
              </ul>
            </div>
            <div class="bg-gray-800/60 rounded p-2 border border-gray-700/60">
              <div class="flex justify-between mb-1">
                <span class="text-gray-400">极端高温预警概率</span>
                <span class="text-yellow-400">67%</span>
              </div>
              <div class="h-1.5 bg-gray-700 rounded overflow-hidden">
                <div class="h-full bg-yellow-400" style="width: 67%"></div>
              </div>
              <p class="text-[10px] text-gray-500 mt-1">未来 6h · 气象服务接入</p>
            </div>
            <div class="bg-gray-800/60 rounded p-2 border border-gray-700/60">
              <div class="flex justify-between mb-1">
                <span class="text-gray-400">凝露触发概率</span>
                <span class="text-green-400">3%</span>
              </div>
              <div class="h-1.5 bg-gray-700 rounded overflow-hidden">
                <div class="h-full bg-green-400" style="width: 3%"></div>
              </div>
            </div>
          </div>
        </div>

        <div class="glass rounded-lg p-3 flex-1 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:clipboard-alert"></iconify-icon> 环境预警 &amp; 处置建议
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

const cams = [
  { name: 'CAM-01 城南500kV', box: true },
  { name: 'CAM-02 城北220kV', box: false },
  { name: 'CAM-03 城东110kV', box: false },
  { name: 'CAM-04 城西110kV', box: false }
]

const envOption = {
  tooltip: { trigger: 'axis', ...TT },
  legend: { textStyle: { color: '#9ca3af', fontSize: 10 }, top: 0, right: 0 },
  grid: { top: 25, bottom: 20, left: 40, right: 40 },
  xAxis: {
    type: 'category',
    data: ['00', '02', '04', '06', '08', '10', '12', '14', '16', '18', '20', '22'],
    ...AXIS
  },
  yAxis: [
    { type: 'value', name: '℃', nameTextStyle: { color: '#9ca3af', fontSize: 10 }, ...AXIS },
    { type: 'value', name: '%', nameTextStyle: { color: '#06b6d4', fontSize: 10 }, ...AXIS, max: 100 }
  ],
  series: [
    {
      name: '温度',
      type: 'line',
      smooth: true,
      data: [26, 24, 22, 24, 28, 31, 34, 36, 38, 37, 33, 29],
      color: '#f59e0b',
      areaStyle: { opacity: 0.15 },
      markLine: {
        symbol: 'none',
        data: [{ yAxis: 40, lineStyle: { color: '#ef4444', type: 'dashed' }, label: { color: '#fca5a5', fontSize: 10, formatter: '报警 40℃' } }]
      }
    },
    {
      name: '湿度',
      type: 'line',
      smooth: true,
      yAxisIndex: 1,
      data: [70, 72, 75, 73, 68, 62, 58, 54, 52, 56, 62, 68],
      color: '#06b6d4',
      markLine: {
        symbol: 'none',
        data: [{ yAxis: 85, lineStyle: { color: '#ef4444', type: 'dashed' }, label: { color: '#fca5a5', fontSize: 10, formatter: '报警 85%' } }]
      }
    }
  ]
}

const siteOption = {
  tooltip: { trigger: 'axis', ...TT },
  legend: { textStyle: { color: '#9ca3af', fontSize: 10 }, top: 0, right: 0 },
  grid: { top: 25, bottom: 20, left: 40, right: 10 },
  xAxis: {
    type: 'category',
    data: ['城南500', '城北220', '城东110', '城西110', '滨江', '开发区', '新城', '工业园'],
    ...AXIS,
    axisLabel: { ...AXIS.axisLabel, interval: 0, rotate: 25 }
  },
  yAxis: [
    { type: 'value', ...AXIS, max: 50 },
    { type: 'value', ...AXIS, max: 100 }
  ],
  series: [
    {
      name: '温度 ℃',
      type: 'bar',
      data: [38, 36, 37, 35, 34, 39, 33, 36],
      itemStyle: { color: (p) => (p.value >= 40 ? '#ef4444' : p.value >= 37 ? '#f59e0b' : '#10b981') },
      barWidth: 14
    },
    {
      name: '湿度 %',
      type: 'line',
      yAxisIndex: 1,
      smooth: true,
      data: [62, 88, 65, 70, 68, 58, 72, 60],
      color: '#06b6d4',
      markLine: { symbol: 'none', data: [{ yAxis: 85, lineStyle: { color: '#ef4444', type: 'dashed' } }] }
    }
  ]
}

const dewOption = {
  tooltip: { trigger: 'axis', ...TT },
  legend: { textStyle: { color: '#9ca3af', fontSize: 10 }, top: 0, right: 0 },
  grid: { top: 25, bottom: 20, left: 35, right: 10 },
  xAxis: {
    type: 'category',
    data: ['00', '03', '06', '09', '12', '15', '18', '21', '24'],
    ...AXIS
  },
  yAxis: { type: 'value', ...AXIS, name: '℃' },
  series: [
    { name: '设备本体温度', type: 'line', smooth: true, data: [45, 42, 40, 44, 50, 54, 56, 50, 45], color: '#f59e0b' },
    {
      name: '露点温度',
      type: 'line',
      smooth: true,
      data: [20, 19, 18, 22, 25, 27, 26, 24, 22],
      color: '#06b6d4',
      areaStyle: { color: 'rgba(6,182,212,.15)' }
    },
    {
      name: '差值阈值 5℃',
      type: 'line',
      data: Array(9).fill(5),
      lineStyle: { type: 'dashed', color: '#ef4444' },
      symbol: 'none'
    }
  ]
}

const alerts = [
  { level: '提示',   tag: 'tag-blu', border: 'border-blue-500',   time: '14:20:00',  msg: '环境温度 38℃ 接近 40℃ 报警阈值',        action: '采取降温措施，加强设备绝缘监测' },
  { level: '提示',   tag: 'tag-blu', border: 'border-blue-500',   time: '14:15:00',  msg: '智能体已联动调整本体温度预警阈值',        action: '环境参数持续恶化 → 动态下调 5%' },
  { level: '一般',   tag: 'tag-yel', border: 'border-yellow-500', time: '昨 03:15:20', msg: '城北220kV 站 湿度 88% 触发凝露报警（已解除）', action: '已启动除湿装置，加强设备绝缘监测' },
  { level: '已处置', tag: 'tag-grn', border: 'border-green-500',  time: '前日 22:30', msg: '城南站 围栏外鸟巢入侵告警',                action: '已派工清除，检查设备防护措施完好' }
]
</script>

<style scoped>
.cctv-mock {
  background: linear-gradient(135deg, #0f172a, #1e293b);
  border: 1px solid rgba(59, 130, 246, .3);
  position: relative;
  overflow: hidden;
}
.cctv-mock::before {
  content: '';
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(16,185,129,.04) 2px, rgba(16,185,129,.04) 4px);
  pointer-events: none;
}
.live-dot {
  width: 6px;
  height: 6px;
  background: #ef4444;
  border-radius: 50%;
  display: inline-block;
  animation: blink 1.5s infinite;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50%      { opacity: .3; }
}
</style>
