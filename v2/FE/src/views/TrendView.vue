<script setup>
// 趋势预警页:DL/T 722 §9.3.2 相对产气速率(%/月)逐日走势 + 「预」点。
// 口径(D-004):722 §9.3.2 相对速率(月环比+连续3天确认),与检测②处置/④预同尺;
// 落档另用 1498.2 表A.3 %/周,不在本页。
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import http from '@/service/http'

const loading = ref(true)
const summary = ref({})
const preEvents = ref([])
const thcAttention = ref(10)
const rateEl = ref(null)
let chart = null

const chartColors = {
  axis: '#7c8aa0',
  split: 'rgba(160, 174, 192, 0.12)',
  text: '#b4c0d4',
  rate: '#2dd4bf',
  attention: '#d9a441',
  firstOver: '#34d399',
  pre: '#fbbf24',
  bg: 'transparent',
}

function renderRate(series) {
  if (!rateEl.value) return
  if (!chart) chart = echarts.init(rateEl.value)
  const days = series.map((s) => s.day)
  const rate = series.map((s) => s.rel_rate)
  const preScatter = series.filter((s) => s.is_pre).map((s) => [s.day, s.rel_rate])
  const firstOver = series.find((s) => s.grade && s.grade !== '正常')

  chart.setOption({
    backgroundColor: chartColors.bg,
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#323e4c',
      borderColor: 'rgba(45, 212, 191, 0.35)',
      textStyle: { color: '#f1f5fb', fontSize: 12 },
      formatter: (ps) => {
        const s = series[ps[0].dataIndex]
        const pre = s.is_pre
          ? '<br/><b style="color:#fbbf24">「预」浓度未超但速率连续超10%/月</b>'
          : ''
        return `第 ${s.day} 天(${s.date})<br/>相对速率:${s.rel_rate ?? '—'} %/月<br/>档位:${s.grade}${pre}`
      },
    },
    legend: {
      data: ['相对产气速率(总烃)', '「预」触发点'],
      top: 4,
      textStyle: { color: chartColors.text, fontSize: 11 },
      itemWidth: 14,
      itemHeight: 8,
    },
    grid: { left: 56, right: 36, top: 40, bottom: 58 },
    xAxis: {
      type: 'category',
      data: days,
      boundaryGap: false,
      axisLine: { lineStyle: { color: chartColors.split } },
      axisLabel: { color: chartColors.axis, fontSize: 10 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      name: '%/月',
      nameTextStyle: { color: chartColors.axis, fontSize: 10 },
      axisLine: { show: false },
      axisLabel: { color: chartColors.axis, fontSize: 10 },
      splitLine: { lineStyle: { color: chartColors.split, type: 'dashed' } },
    },
    dataZoom: [
      { type: 'inside' },
      {
        type: 'slider',
        bottom: 6,
        height: 16,
        start: 0,
        end: 100,
        borderColor: 'rgba(160,174,192,0.26)',
        backgroundColor: 'rgba(33,43,56,0.8)',
        fillerColor: 'rgba(45,212,191,0.18)',
        handleStyle: { color: '#2dd4bf' },
        textStyle: { color: chartColors.axis, fontSize: 10 },
      },
    ],
    series: [
      {
        name: '相对产气速率(总烃)',
        type: 'line',
        data: rate,
        showSymbol: false,
        lineStyle: { color: chartColors.rate, width: 1.6 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(45, 212, 191, 0.28)' },
            { offset: 1, color: 'rgba(45, 212, 191, 0.02)' },
          ]),
        },
        markLine: {
          symbol: 'none',
          silent: true,
          data: [
            {
              yAxis: thcAttention.value,
              lineStyle: { color: chartColors.attention, type: 'dashed', width: 1.2 },
              label: {
                formatter: '10%/月 注意线',
                color: chartColors.attention,
                position: 'insideEndTop',
                fontSize: 10,
              },
            },
            ...(firstOver
              ? [{
                  xAxis: firstOver.day,
                  lineStyle: { color: chartColors.firstOver, type: 'dashed', width: 1 },
                  label: {
                    formatter: `首次浓度超标\n第${firstOver.day}天`,
                    color: chartColors.firstOver,
                    fontSize: 10,
                  },
                }]
              : []),
          ],
        },
      },
      {
        name: '「预」触发点',
        type: 'scatter',
        data: preScatter,
        symbolSize: 9,
        itemStyle: {
          color: chartColors.pre,
          shadowBlur: 8,
          shadowColor: 'rgba(251, 191, 36, 0.45)',
        },
        z: 5,
      },
    ],
  })
}

function onResize() {
  chart?.resize()
}

onMounted(async () => {
  try {
    const res = await http.get('/trend/daily')
    summary.value = res.summary
    preEvents.value = res.pre_events
    thcAttention.value = res.thc_attention
    renderRate(res.series)
    window.addEventListener('resize', onResize)
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
  chart = null
})
</script>

<template>
  <div v-loading="loading" class="trend">
    <div class="gf">
      <div class="gp c3">
        <div class="stat s-amber">
          <div class="stat-name">当前总烃相对产气速率</div>
          <div class="stat-val" style="color: var(--amber-2)">
            {{ summary.latest_rate ?? '—' }}<span class="u">%/月</span>
          </div>
          <div class="stat-sub" style="color: var(--fg-3)">第 {{ summary.latest_day ?? '—' }} 天 · 注意线 10%/月</div>
        </div>
      </div>
      <div class="gp c3">
        <div class="stat s-teal">
          <div class="stat-name">「预」事件总数</div>
          <div class="stat-val" style="color: var(--teal-2)">
            {{ summary.pre_count ?? 0 }}<span class="u">次</span>
          </div>
          <div class="stat-sub" style="color: var(--fg-3)">浓度未超但速率连续超 10%/月</div>
        </div>
      </div>
      <div class="gp c3">
        <div class="stat s-w1">
          <div class="stat-name">首次浓度超标日</div>
          <div class="stat-val">第 {{ summary.first_over_day ?? '—' }}<span class="u">天</span></div>
          <div class="stat-sub" style="color: var(--fg-3)">{{ summary.first_over_date || '—' }}</div>
        </div>
      </div>
      <div class="gp c3">
        <div class="stat s-normal">
          <div class="stat-name">监测总天数</div>
          <div class="stat-val" style="color: var(--lv-normal)">
            {{ summary.total_days ?? '—' }}<span class="u">天</span>
          </div>
          <div class="stat-sub" style="color: var(--fg-3)">合成单台 × 360 天</div>
        </div>
      </div>

      <div class="gp c8">
        <div class="gp-head">
          360 天总烃相对产气速率
          <span class="std">§9.3.2 式2</span>
        </div>
        <div class="gp-body">
          <div ref="rateEl" class="chart" />
          <div class="gf-legend">
            <span><i style="background: #2dd4bf" />相对产气速率</span>
            <span><i style="border-top: 2px dashed #d9a441; height: 0; background: transparent" />10%/月 注意线</span>
            <span><i class="dot" style="background: #fbbf24" />「预」触发点</span>
          </div>
        </div>
      </div>

      <div class="gp c4">
        <div class="gp-head">
          产气速率计算说明
          <span class="std">表4 / 式2</span>
        </div>
        <div class="gp-body">
          <div class="note info" style="margin-bottom: 10px">
            相对速率(式2)只需前后两次浓度,本系统采用;绝对速率(式1)需油重/油密度,合成数据无 → 标「—」(诚实)。
          </div>
          <div class="calc-body">
            <div><b>相对产气速率(式2)</b></div>
            <div class="mono formula">γᵣ = (C₂ − C₁) / C₁ × 1/Δt × 100%</div>
            <div style="margin-top: 8px; color: var(--fg-3)">
              本页取月环比(今 vs 30 天前);总烃注意值 <b class="mono">10%/月</b>;总烃&lt;10μL/L 不宜用。
            </div>
            <div style="margin-top: 10px; color: var(--fg-4); font-size: 11px">
              表4 绝对产气率注意值(mL/d,密封式): H₂ 10 · C₂H₂ 0.2 · 总烃 12 · CO 100 · CO₂ 200
            </div>
          </div>
        </div>
      </div>

      <div class="gp c12">
        <div class="gp-head">
          「预」事件明细 · 气体未超标但产气速率已超注意值
          <span class="std">§9.3.3 a)</span>
        </div>
        <div class="gp-body tight">
          <el-table :data="preEvents" stripe empty-text="无「预」事件" style="width: 100%">
            <el-table-column type="index" label="序号" width="64" />
            <el-table-column prop="date" label="日期" width="120" />
            <el-table-column prop="day" label="第几天" width="84" />
            <el-table-column prop="grade" label="当日档位" width="96">
              <template #default="{ row }">
                <span
                  class="pill"
                  :class="{
                    normal: row.grade === '正常',
                    w1: row.grade === '注意值1',
                    w2: row.grade === '注意值2',
                    alarm: row.grade === '告警值',
                  }"
                >
                  <i class="d" />{{ row.grade }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="total_hydrocarbon" label="总烃(μL/L)" width="110" align="right">
              <template #default="{ row }">
                <span class="mono">{{ row.total_hydrocarbon }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="rel_rate" label="相对速率(%/月)" width="130" align="right">
              <template #default="{ row }">
                <span class="rate-hot mono">{{ row.rel_rate?.toFixed(1) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="basis" label="命中判据" min-width="220" />
            <el-table-column prop="advice" label="建议" min-width="160" />
          </el-table>
        </div>
      </div>
    </div>

    <div class="note warn" style="margin-top: 10px">
      口径(D-004):DL/T 722 §9.3.2 相对产气速率(%/月,月环比 + 连续3天确认);
      「预」= 浓度未超注意值但速率连续超 10%/月 →§9.3.3 a) 缩短检测周期。
      落档另用 DL/T 1498.2 表A.3(%/周),不在本页。异常段速率爬坡幅度大,拖动图下滑块可放大看清 10%/月 注意线与「预」点。
    </div>
  </div>
</template>

<style scoped>
.trend {
  min-height: 200px;
}

.chart {
  width: 100%;
  height: 280px;
}

.calc-body {
  font-size: 12px;
  line-height: 1.7;
  color: var(--fg-2);
}

.formula {
  margin-top: 4px;
  color: var(--teal-2);
  font-size: 12.5px;
}

.rate-hot {
  color: var(--lv-w1);
  font-weight: 600;
}

.pill {
  font-size: 11px;
}
</style>
