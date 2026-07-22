<script setup>
// 产气趋势 —— 模块3 辅线:
// 722 §9.3.2 相对产气速率(%/月)走势 + 「预」提前预警(§9.3.3 a)
// 与表A.3 周增率两套不换算(D-004);不做预测模型
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts'
import http from '@/service/http'
import StdCite from '@/components/StdCite.vue'
import TablePager from '@/components/TablePager.vue'

const loading = ref(true)
const route = useRoute()
const series = ref([])
const summary = ref({})
const preEvents = ref([])
const thcAttention = ref(10)
const lookback = ref(30)

const windowMode = ref('90') // '90' | 'all'
const prePage = ref(1)
const prePageSize = ref(10)
const selectedDay = ref(null)

const rateEl = ref(null)
let rateChart = null

const colors = {
  axis: '#7c8aa0',
  split: 'rgba(160, 174, 192, 0.12)',
  text: '#b4c0d4',
  rate: '#2dd4bf',
  attention: '#d9a441',
  pre: '#a78bfa', // 对齐 --lv-pre
  rising: '#fb923c',
}

const gradeClass = (g) => ({
  正常: 'normal', 注意值1: 'w1', 注意值2: 'w2', 告警值: 'alarm',
}[g] || 'normal')

const viewSeries = computed(() => {
  if (windowMode.value === 'all') return series.value
  return series.value.slice(-90)
})

const preSorted = computed(() =>
  [...preEvents.value].sort((a, b) => b.day - a.day),
)

const prePageRows = computed(() => {
  const start = (prePage.value - 1) * prePageSize.value
  return preSorted.value.slice(start, start + prePageSize.value)
})

const selected = computed(() => {
  if (selectedDay.value == null) return null
  return series.value.find((s) => s.day === selectedDay.value) || null
})

const latestOver = computed(() => {
  const r = summary.value.latest_rate
  return r != null && r >= thcAttention.value
})

watch(windowMode, () => nextTick(() => renderRate()))

function focusDay(day) {
  selectedDay.value = day
  // 窗口外 → 切全年
  if (windowMode.value === '90' && series.value.length > 90) {
    const startDay = series.value[series.value.length - 90]?.day
    if (day < startDay) windowMode.value = 'all'
  }
  // 若该日在涨势预警列表，翻到对应页
  const preIdx = preSorted.value.findIndex((r) => r.day === day)
  if (preIdx >= 0) {
    prePage.value = Math.floor(preIdx / prePageSize.value) + 1
  }
  nextTick(() => renderRate())
}

function selectPre(row) {
  focusDay(row.day)
}

function selectDayByIndex(idx) {
  const s = viewSeries.value[idx]
  if (!s) return
  focusDay(s.day)
}

function renderRate() {
  if (!rateEl.value) return
  if (!rateChart) rateChart = echarts.init(rateEl.value)
  const data = viewSeries.value
  const days = data.map((s) => s.day)
  const rate = data.map((s) => s.rel_rate)
  const preScatter = data.filter((s) => s.is_pre).map((s) => [String(s.day), s.rel_rate])
  const markX = selected.value && data.some((s) => s.day === selected.value.day)
    ? selected.value.day
    : null

  // 有选中日时，把 dataZoom 拉到该日附近，避免「看似没定位」
  let zoomRange = { start: 0, end: 100 }
  if (markX != null && data.length > 1) {
    const idx = data.findIndex((s) => s.day === markX)
    if (idx >= 0) {
      const half = Math.max(8, Math.floor(data.length * 0.08))
      const lo = Math.max(0, idx - half)
      const hi = Math.min(data.length - 1, idx + half)
      zoomRange = {
        start: (lo / (data.length - 1)) * 100,
        end: (hi / (data.length - 1)) * 100,
      }
    }
  }

  rateChart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#323e4c',
      borderColor: 'rgba(45, 212, 191, 0.35)',
      textStyle: { color: '#f1f5fb', fontSize: 12 },
      formatter: (ps) => {
        const idx = ps[0].dataIndex
        const s = data[idx]
        if (!s) return ''
        let extra = ''
        if (s.is_pre) extra = '<br/><b style="color:var(--lv-pre-2,#c4b5fd)">涨势预警 · 档未达注意值2,速率超注意值</b>'
        else if (s.urgency_rising) extra = '<br/><span style="color:#fb923c">涨势确认(注意值2+ 处置急)</span>'
        else if (s.rel_rate != null && s.rel_rate >= thcAttention.value) {
          extra = '<br/><span style="color:#d9a441">速率超注意但档位已到注意值2+</span>'
        }
        return `第 ${s.day} 天 · ${s.date}<br/>月环比 ${s.rel_rate ?? '—'} %/月<br/>当日最高档 ${s.grade}${extra}`
      },
    },
    legend: {
      data: ['总烃月环比', '涨势预警'],
      top: 4,
      textStyle: { color: colors.text, fontSize: 11 },
      itemWidth: 14,
      itemHeight: 8,
    },
    grid: { left: 52, right: 28, top: 36, bottom: 52 },
    xAxis: {
      type: 'category',
      data: days,
      boundaryGap: false,
      axisLine: { lineStyle: { color: colors.split } },
      axisLabel: { color: colors.axis, fontSize: 10 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      name: '%/月',
      nameTextStyle: { color: colors.axis, fontSize: 10 },
      axisLine: { show: false },
      axisLabel: { color: colors.axis, fontSize: 10 },
      splitLine: { lineStyle: { color: colors.split, type: 'dashed' } },
    },
    dataZoom: [
      { type: 'inside', start: zoomRange.start, end: zoomRange.end },
      {
        type: 'slider',
        bottom: 6,
        height: 14,
        start: zoomRange.start,
        end: zoomRange.end,
        borderColor: 'rgba(160,174,192,0.26)',
        backgroundColor: 'rgba(33,43,56,0.8)',
        fillerColor: 'rgba(45,212,191,0.18)',
        handleStyle: { color: '#2dd4bf' },
        textStyle: { color: colors.axis, fontSize: 10 },
      },
    ],
    series: [
      {
        name: '总烃月环比',
        type: 'line',
        data: rate,
        showSymbol: false,
        connectNulls: false,
        lineStyle: { color: colors.rate, width: 1.6 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(45, 212, 191, 0.22)' },
            { offset: 1, color: 'rgba(45, 212, 191, 0.02)' },
          ]),
        },
        markLine: {
          symbol: 'none',
          silent: true,
          data: [
            {
              yAxis: thcAttention.value,
              lineStyle: { color: colors.attention, type: 'dashed', width: 1.2 },
              label: {
                formatter: `${thcAttention.value}%/月`,
                color: colors.attention,
                position: 'insideEndTop',
                fontSize: 10,
              },
            },
            ...(markX != null
              ? [{
                  xAxis: String(markX),
                  lineStyle: { color: colors.pre, type: 'solid', width: 1.5 },
                  label: {
                    formatter: selected.value?.date || `D${markX}`,
                    color: colors.pre,
                    fontSize: 11,
                    fontWeight: 600,
                  },
                }]
              : []),
          ],
        },
      },
      {
        name: '涨势预警',
        type: 'scatter',
        data: preScatter,
        symbolSize: 10,
        itemStyle: {
          color: colors.pre,
          shadowBlur: 8,
          shadowColor: 'rgba(251, 191, 36, 0.45)',
        },
        z: 5,
      },
    ],
  }, true)

  rateChart.off('click')
  rateChart.on('click', (params) => {
    if (params?.componentType === 'series' && typeof params.dataIndex === 'number') {
      selectDayByIndex(params.dataIndex)
    }
  })
}


function onResize() {
  rateChart?.resize()
}

function applyDateQuery() {
  const q = typeof route.query.date === 'string' ? route.query.date : ''
  if (!q || !series.value.length) return
  const hit = series.value.find((s) => s.date === q)
  if (!hit) return
  focusDay(hit.day)
}

onMounted(async () => {
  try {
    const daily = await http.get('/trend/daily')
    series.value = daily.series || []
    summary.value = daily.summary || {}
    preEvents.value = daily.pre_events || []
    thcAttention.value = daily.thc_attention ?? 10
    lookback.value = daily.lookback_days ?? 30
    await nextTick()
    applyDateQuery()
    if (!selectedDay.value) renderRate()
    window.addEventListener('resize', onResize)
  } finally {
    loading.value = false
  }
})

watch(() => route.query.date, () => applyDateQuery())

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  rateChart?.dispose()
  rateChart = null
})
</script>

<template>
  <div v-loading="loading" class="trend">
    <!-- KPI：一眼看涨势强度与预警次数 -->
    <div class="kpis">
      <div class="kpi">
        <div class="kpi-k">当前总烃月环比</div>
        <div class="kpi-v" :class="{ hot: latestOver }">
          {{ summary.latest_rate ?? '—' }}<span class="u">%/月</span>
        </div>
        <div class="kpi-s">最新日 · 注意线 {{ thcAttention }}%/月 <StdCite ref-id="722-9.3.2" label="§9.3.2" inline /></div>
      </div>
      <div class="kpi">
        <div class="kpi-k">涨势预警</div>
        <div class="kpi-v pre">{{ summary.pre_count ?? 0 }}<span class="u">次</span></div>
        <div class="kpi-s">全年触发次数（档位正常/注意值1，且月环比超注意值）</div>
      </div>
    </div>

    <!-- 逐日曲线 -->
    <section class="gp">
      <div class="gp-head toolbar">
        <span>
          总烃相对产气速率（月环比）
          <StdCite ref-id="722-9.3.2" label="§9.3.2" />
        </span>
        <div class="chips">
          <button type="button" class="chip" :class="{ on: windowMode === '90' }" @click="windowMode = '90'">近 90 天</button>
          <button type="button" class="chip" :class="{ on: windowMode === 'all' }" @click="windowMode = 'all'">全年 360 天</button>
        </div>
        <span class="head-ref">紫点 = 涨势预警 · 虚线 = {{ thcAttention }}%/月</span>
      </div>
      <div v-if="selected" class="focus-bar">
        <span class="focus-k">定位</span>
        <span class="mono">{{ selected.date }}</span>
        <span class="pill mini" :class="gradeClass(selected.grade)"><i class="d" />{{ selected.grade }}</span>
        <span class="mono" :class="{ hot: selected.rel_rate != null && selected.rel_rate >= thcAttention }">
          {{ selected.rel_rate ?? '—' }}%/月
        </span>
        <span v-if="selected.is_pre" class="pre-tag">涨势预警</span>
      </div>
      <div class="gp-body">
        <div ref="rateEl" class="chart-tall" />
        <div class="formula-bar">
          <span class="f-label">相对产气速率</span>
          <span class="f-mono">γ<sub>r</sub> = (C<sub>2</sub> − C<sub>1</sub>) / C<sub>1</sub> × 100%　·　Δt = 1 月（今 vs {{ lookback }} 天前）</span>
        </div>
      </div>
    </section>

    <section class="gp pre-panel">
        <div class="gp-head">
          涨势预警列表
          <span class="head-ref">共 {{ preSorted.length }} 条 · 点击同步高亮曲线</span>
        </div>
        <div class="table-wrap table-wrap--compact">
          <table class="dga-table">
            <thead>
              <tr>
                <th>日期</th>
                <th>档位</th>
                <th class="num">当日总烃</th>
                <th class="num">{{ lookback }}天前</th>
                <th class="num">月环比</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="r in prePageRows"
                :key="r.date"
                class="clickable"
                :class="{ on: selectedDay === r.day }"
                @click="selectPre(r)"
              >
                <td class="mono">{{ r.date }}</td>
                <td>
                  <span class="pill mini" :class="gradeClass(r.grade)"><i class="d" />{{ r.grade }}</span>
                </td>
                <td class="num mono">{{ r.total_hydrocarbon ?? '—' }}</td>
                <td class="num mono">{{ r.thc_base ?? '—' }}</td>
                <td class="num mono hot">{{ r.rel_rate ?? '—' }}%/月</td>
              </tr>
              <tr v-if="!prePageRows.length">
                <td colspan="5" class="empty">暂无涨势预警</td>
              </tr>
            </tbody>
          </table>
        </div>
        <TablePager
          v-model:page="prePage"
          v-model:page-size="prePageSize"
          :total="preSorted.length"
          :page-size-options="[10, 20, 50]"
          empty-text="无涨势预警"
        />
    </section>
  </div>
</template>

<style scoped>
.trend { display: flex; flex-direction: column; gap: 12px; }

.kpis {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
@media (max-width: 700px) {
  .kpis { grid-template-columns: 1fr; }
}
.kpi {
  padding: 12px 14px;
  border-radius: var(--r);
  background: var(--bg-2);
  border: 1px solid var(--line);
}
.kpi-k { font-size: 11px; color: var(--fg-3); }
.kpi-v {
  font-size: 26px; font-weight: 800; color: var(--fg); margin: 2px 0;
  font-family: 'JetBrains Mono', monospace;
}
.kpi-v .u { font-size: 12px; font-weight: 600; color: var(--fg-4); margin-left: 2px; }
.kpi-v.hot { color: #fbbf24; }
.kpi-v.pre { color: var(--lv-pre-2); }
.kpi-s { font-size: 11px; color: var(--fg-4); line-height: 1.45; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }

.toolbar { flex-wrap: wrap; gap: 10px; align-items: center; }
.chips { display: flex; gap: 6px; }
.chip {
  border: 1px solid var(--line);
  background: var(--bg-3);
  color: var(--fg-3);
  font-size: 11px; font-weight: 600;
  padding: 3px 10px; border-radius: 999px;
  cursor: pointer;
}
.chip.on {
  border-color: rgba(45,212,191,0.45);
  color: var(--teal-2);
  background: rgba(45,212,191,0.1);
}
.head-ref { margin-left: auto; font-size: 11px; color: var(--fg-4); font-weight: 500; }

.focus-bar {
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px 10px;
  padding: 8px 14px;
  border-bottom: 1px solid var(--line);
  background: rgba(167, 139, 250, 0.06);
  font-size: 12px;
}
.focus-k {
  font-size: 10px; font-weight: 700; color: var(--lv-pre-2, #c4b5fd);
  letter-spacing: 0.04em;
}
.focus-bar .hot { color: #fbbf24; font-weight: 700; }

.chart-tall { width: 100%; height: 300px; }


.formula-bar {
  display: flex; flex-wrap: wrap; align-items: baseline; gap: 10px 14px;
  margin-top: 8px; padding-top: 10px; border-top: 1px solid var(--line);
  font-size: 12px;
}
.f-label {
  font-size: 10px; font-weight: 700; color: var(--teal-2);
  padding: 1px 6px; border-radius: 4px;
  border: 1px solid rgba(45,212,191,0.3);
}
.f-mono {
  font-family: 'JetBrains Mono', 'Times New Roman', serif;
  color: var(--fg);
  font-weight: 600;
}
.f-mono sub { font-size: 0.75em; }

.pre-panel { display: flex; flex-direction: column; min-height: 0; }
.mono { font-family: 'JetBrains Mono', monospace; }
.hot { color: #fbbf24; font-weight: 700; }
.pill.mini { font-size: 10px; padding: 2px 8px; }

</style>
