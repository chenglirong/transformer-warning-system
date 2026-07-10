<script setup>
// 趋势预警页:DL/T 722 §9.3.2 式2 月度相对产气速率(%/月)+ 总烃 10%/月 判据。
// 口径(D-004):本页用 722 式2(%/月·相邻两月均值),只做月度产气趋势展示 +
// 总烃判据旁证,不落档、不承担「预」(「预」由检测页表A.3 %/周落档)。
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'
import { getTrendMonthly } from '@/service/api'

const loading = ref(true)
const thcAttention = ref(10)
const alertMonths = ref([])
const concEl = ref(null)   // 总烃月均浓度曲线
const rateEl = ref(null)   // 总烃相对产气速率(%/月)柱 + 10%/月 判据线

function renderConc(points) {
  const chart = echarts.init(concEl.value)
  const months = points.map((p) => p.month)
  const thc = points.map((p) => p.total_hydrocarbon)
  chart.setOption({
    title: { text: '总烃月均浓度(μL/L)', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 30, top: 50, bottom: 40 },
    xAxis: { type: 'category', data: months },
    yAxis: { type: 'value', name: 'μL/L' },
    series: [{ type: 'line', data: thc, smooth: true, areaStyle: {},
      lineStyle: { color: '#2563eb' }, itemStyle: { color: '#2563eb' } }],
  })
}

function renderRate(points) {
  const chart = echarts.init(rateEl.value)
  const months = points.map((p) => p.month)
  // 首月无上月速率为 null;超 10%/月 标红
  const data = points.map((p) => {
    const v = p.rates.total_hydrocarbon
    return {
      value: v,
      itemStyle: { color: p.thc_alert ? '#dc2626' : (v == null ? '#d1d5db' : '#10b981') },
    }
  })
  chart.setOption({
    title: { text: '总烃相对产气速率(%/月,式2)', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {
      trigger: 'axis',
      formatter: (ps) => {
        const p = points[ps[0].dataIndex]
        const r = p.rates.total_hydrocarbon
        const tag = p.thc_alert === null ? '不适用(总烃<10μL/L)'
          : p.thc_alert ? '⚠️ 超 10%/月 注意值' : '正常'
        return `${p.month}<br/>相对速率:${r == null ? '—' : r + ' %/月'}<br/>${tag}`
      },
    },
    grid: { left: 60, right: 30, top: 50, bottom: 40 },
    xAxis: { type: 'category', data: months },
    yAxis: { type: 'value', name: '%/月' },
    series: [{
      type: 'bar', data,
      markLine: {
        symbol: 'none', silent: true,
        data: [{ yAxis: thcAttention.value, name: '注意值 10%/月' }],
        lineStyle: { color: '#dc2626', type: 'dashed' },
        label: { formatter: '10%/月 注意值', color: '#dc2626' },
      },
    }],
  })
}

onMounted(async () => {
  try {
    const res = await getTrendMonthly()
    thcAttention.value = res.thc_attention
    alertMonths.value = res.alert_months
    renderConc(res.points)
    renderRate(res.points)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div v-loading="loading" class="trend">
    <div class="head">
      <h2>趋势预警 · 月度产气速率</h2>
      <p class="sub">
        DL/T 722 §9.3.2 式2 相对产气速率(%/月);仅总烃有 10%/月 注意值。
        本页为月度趋势展示,档位落档见检测页(表A.3 %/周)。
      </p>
    </div>
    <el-alert v-if="alertMonths.length" type="warning" :closable="false" class="alert"
      :title="`超 10%/月 注意值的月份:${alertMonths.join('、')}`" />
    <div class="charts">
      <div ref="concEl" class="chart"></div>
      <div ref="rateEl" class="chart"></div>
    </div>
  </div>
</template>

<style scoped>
.trend { display: flex; flex-direction: column; gap: 16px; }
.head h2 { margin: 0 0 4px; font-size: 18px; }
.sub { margin: 0; color: #6b7280; font-size: 13px; }
.alert { margin: 0; }
.charts { display: flex; flex-direction: column; gap: 16px; }
.chart { width: 100%; height: 320px; background: #fff; border-radius: 8px;
  padding: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
</style>
