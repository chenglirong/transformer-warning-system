<script setup>
// 故障类型判断页 —— 三方法对标参考页信息密度:
// 三比值表+编码块 / 大卫三角图 / 特征气体雷达+含量表 → 一致性结论
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'
import http from '@/service/http'
import StdCite from '@/components/StdCite.vue'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const series = ref([])
const summary = ref({})
const selectedDate = ref('')
const detail = ref(null)
const dayLoading = ref(false)

const radarEl = ref(null)
let radarChart = null

const diagnosis = computed(() => detail.value?.diagnosis || null)
const triggered = computed(() => !!diagnosis.value?.triggered)
const fusion = computed(() => diagnosis.value?.fusion || null)
const ratios = computed(() => diagnosis.value?.ratios || null)
const duval = computed(() => diagnosis.value?.duval || null)
const keyGas = computed(() => diagnosis.value?.key_gas || null)

const current = computed(() => series.value.find((s) => s.date === selectedDate.value))
const idx = computed(() => series.value.findIndex((s) => s.date === selectedDate.value))

const dateRange = computed(() => {
  if (!series.value.length) return null
  return [series.value[0].date, series.value[series.value.length - 1].date]
})

const gradeClass = (g) => ({
  正常: 'normal', 注意值1: 'w1', 注意值2: 'w2', 告警值: 'alarm',
}[g] || 'normal')

const confidenceClass = computed(() => {
  const c = fusion.value?.confidence
  if (c === '高') return 'high'
  if (c === '低') return 'low'
  return 'mid'
})

/** 表6 三位编码顺序:C2H2/C2H4 · CH4/H2 · C2H4/C2H6 */
const RATIO_ROWS = [
  { key: 'C2H2/C2H4', label: 'C₂H₂ / C₂H₄', sub: '表6 第1位' },
  { key: 'CH4/H2', label: 'CH₄ / H₂', sub: '表6 第2位' },
  { key: 'C2H4/C2H6', label: 'C₂H₄ / C₂H₆', sub: '表6 第3位' },
]

const ratioRows = computed(() => {
  const r = ratios.value
  if (!r?.ok || !r.ratios) return []
  return RATIO_ROWS.map((row, i) => ({
    ...row,
    value: r.ratios[row.key],
    code: r.code?.[i],
  }))
})

const codeTone = (c) => {
  if (c === 0) return 'c0'
  if (c === 1) return 'c1'
  if (c === 2) return 'c2'
  return ''
}

const HERO_BY_CODE = {
  T1: '热故障 <300℃ · T1',
  T2: '热故障 300~700℃ · T2',
  T3: '高温过热 · T3',
  D1: '低能放电 · D1',
  D2: '高能放电 · D2',
  PD: '局部放电 · PD',
  DT: '放电兼过热 · D+T',
}
const heroTitle = computed(() => {
  const f = fusion.value
  if (!f) return '—'
  if (f.primary_code && HERO_BY_CODE[f.primary_code]) return HERO_BY_CODE[f.primary_code]
  return f.primary
})

const methodResults = computed(() => [
  {
    name: '三比值法',
    value: ratios.value?.ok
      ? (ratios.value.duval_code
        ? `${ratios.value.duval_code} · ${ratios.value.fault}`
        : ratios.value.fault)
      : (ratios.value?.fault || '—'),
  },
  {
    name: '大卫三角',
    value: duval.value?.ok
      ? `${duval.value.zone} · ${duval.value.fault}`
      : (duval.value?.fault || '—'),
  },
  {
    name: '特征气体',
    value: keyGas.value?.fault || '—',
  },
])

const consistencyLabel = computed(() => {
  const f = fusion.value
  if (!f) return '—'
  if (f.ratio_duval_consistent && f.nature_agree) return `一致（${f.nature_label}）`
  if (f.ratio_duval_consistent === false) return '落格不一致'
  if (f.nature_agree === false) return '性质不完全一致'
  return '部分有效'
})

const consistencyOk = computed(() => {
  const f = fusion.value
  return !!(f?.ratio_duval_consistent && f?.nature_agree)
})

const isProvisional = computed(() =>
  !!fusion.value?.provisional || fusion.value?.confidence === '低' || fusion.value?.stance === 'provisional',
)

const measuresPurpose = computed(() =>
  fusion.value?.measures_purpose || (isProvisional.value ? 'verify' : 'recommend'),
)

/** 判型页只留对表钩子；完整试验在 Agent */
const measuresHook = computed(() => {
  const f = fusion.value
  if (!f) return ''
  const stance = isProvisional.value ? '暂定' : ''
  const nature = f.measures_nature_label || f.nature_label || '—'
  const code = f.primary_code ? `（${f.primary_code}）` : ''
  const typeTag = stance ? `${stance}「${nature}」` : `「${nature}」`
  const clauses = (f.measures_1685_items || []).map((x) => x.clause).filter(Boolean)
  let s = `当前状况：${typeTag}${code} → 对应 722 表D.1「${nature}」列`
  if (clauses.length) s += `、1685 表${clauses.join('/')}`
  s += ' · 其他检查性试验见分析编排'
  return s
})

function goAgentTrials() {
  router.push({ name: 'agent', query: selectedDate.value ? { date: selectedDate.value } : {} })
}

/** 研判链路：进入门槛 + 三法依表结论（不含综合，右侧独占） */
const reasoningSteps = computed(() => {
  const f = fusion.value
  if (!f) return []
  const head = []
  if (detail.value?.grade || diagnosis.value?.trigger_note) {
    head.push({
      label: '进入判型',
      text: diagnosis.value?.trigger_note || `档位「${detail.value?.grade}」达判型门槛`,
      cite: '722-10.3',
    })
  }
  if (Array.isArray(f.reasoning) && f.reasoning.length) {
    return [...head, ...f.reasoning]
  }
  const steps = [...head]
  methodResults.value.forEach((m, i) => {
    const cites = ['722-表6-7', '722-附录C', '722-表5']
    steps.push({ label: m.name, text: m.value, cite: cites[i] })
  })
  return steps
})

const GAS_GRID = [
  { key: 'h2', label: 'H₂' },
  { key: 'ch4', label: 'CH₄' },
  { key: 'c2h2', label: 'C₂H₂' },
  { key: 'c2h4', label: 'C₂H₄' },
  { key: 'c2h6', label: 'C₂H₆' },
  { key: 'co', label: 'CO' },
  { key: 'co2', label: 'CO₂' },
]

const gasGrid = computed(() => {
  const g = detail.value?.gases || {}
  const elevated = new Set((keyGas.value?.elevated || []).map((x) => x.toLowerCase()))
  return GAS_GRID.map((row) => {
    let raw = g[row.key]
    if (row.key === 'co') raw = detail.value?.co ?? raw
    if (row.key === 'co2') raw = detail.value?.co2 ?? raw
    return {
      ...row,
      value: raw == null ? null : Number(raw),
      hot: elevated.has(row.key),
    }
  })
})

// —— Duval ——
const TOP = { x: 200, y: 28 }
const LEFT = { x: 28, y: 330 }
const RIGHT = { x: 372, y: 330 }

function xy(c2h2, c2h4, ch4) {
  const s = c2h2 + c2h4 + ch4
  const a = c2h2 / s
  const b = c2h4 / s
  const c = ch4 / s
  return `${(a * LEFT.x + b * RIGHT.x + c * TOP.x).toFixed(1)},${(a * LEFT.y + b * RIGHT.y + c * TOP.y).toFixed(1)}`
}
function poly(verts) {
  return verts.map(([a, b, c]) => xy(a, b, c)).join(' ')
}
const ZONES = [
  { id: 'PD', fill: 'rgba(96,165,250,0.45)', label: [1, 1, 98], text: 'PD',
    verts: [[0, 0, 100], [2, 0, 98], [0, 2, 98]] },
  { id: 'D1', fill: 'rgba(52,211,153,0.28)', label: [55, 8, 37], text: 'D1',
    verts: [[13, 0, 87], [100, 0, 0], [77, 23, 0], [13, 23, 64]] },
  { id: 'D2', fill: 'rgba(245,85,90,0.32)', label: [35, 50, 15], text: 'D2',
    verts: [[13, 23, 64], [13, 87, 0], [77, 23, 0]] },
  { id: 'T1', fill: 'rgba(250,204,21,0.28)', label: [2, 5, 93], text: 'T1',
    verts: [[0, 0, 100], [0, 10, 90], [4, 10, 86], [4, 0, 96]] },
  { id: 'T2', fill: 'rgba(251,146,60,0.28)', label: [2, 30, 68], text: 'T2',
    verts: [[0, 10, 90], [0, 50, 50], [4, 50, 46], [4, 10, 86]] },
  { id: 'T3', fill: 'rgba(167,139,250,0.32)', label: [5, 70, 25], text: 'T3',
    verts: [[0, 50, 50], [0, 100, 0], [13, 87, 0], [13, 50, 37]] },
  { id: 'DT', fill: 'rgba(45,212,191,0.16)', label: [8, 25, 67], text: 'D+T',
    verts: [[4, 0, 96], [13, 0, 87], [13, 23, 64], [13, 50, 37], [4, 50, 46], [4, 10, 86]] },
]
/** 附录C 六分区：代码 + 具体类型名，单行图例 */
const ZONE_LEGEND = [
  { id: 'PD', name: '局部放电', color: '#60a5fa' },
  { id: 'D1', name: '低能放电', color: '#34d399' },
  { id: 'D2', name: '高能放电', color: '#f5555a' },
  { id: 'T1', name: '热故障<300℃', color: '#facc15' },
  { id: 'T2', name: '热故障300~700℃', color: '#fb923c' },
  { id: 'T3', name: '热故障>700℃', color: '#a78bfa' },
  { id: 'D+T', name: '放电兼过热', color: '#2dd4bf' },
]

const point = computed(() => {
  const p = duval.value?.percents
  if (!p) return null
  const [x, y] = xy(p.pct_c2h2, p.pct_c2h4, p.pct_ch4).split(',').map(Number)
  return { x, y }
})
const labelPos = (v) => {
  const [x, y] = xy(...v).split(',').map(Number)
  return { x, y }
}

function disabledDate(d) {
  if (!dateRange.value) return true
  const iso = formatDate(d)
  return iso < dateRange.value[0] || iso > dateRange.value[1]
}
/** 日历色标：与检测页同一套 det-*（样式在 global.css，弹层随时可用） */
function cellClassName(d) {
  const iso = formatDate(d)
  const hit = series.value.find((s) => s.date === iso)
  if (!hit) return ''
  if (hit.is_pre) return 'det-pre'
  if (hit.grade === '告警值') return 'det-alarm'
  if (hit.grade === '注意值2') return 'det-w2'
  if (hit.grade === '注意值1') return 'det-w1'
  if (hit.grade === '正常') return 'det-normal'
  return ''
}
function formatDate(d) {
  if (!d) return ''
  if (typeof d === 'string') return d.slice(0, 10)
  if (typeof d.format === 'function') return d.format('YYYY-MM-DD')
  const dt = d instanceof Date ? d : new Date(d)
  if (Number.isNaN(dt.getTime())) return ''
  const y = dt.getFullYear()
  const m = String(dt.getMonth() + 1).padStart(2, '0')
  const day = String(dt.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}
function stepDay(delta) {
  const i = idx.value + delta
  if (i < 0 || i >= series.value.length) return
  selectedDate.value = series.value[i].date
}

function renderRadar() {
  if (!radarEl.value || !triggered.value) return
  const vals = gasGrid.value.map((g) => {
    const v = g.value
    if (v == null || v <= 0) return 0.01
    return Math.max(0.01, v)
  })
  if (!radarChart) radarChart = echarts.init(radarEl.value)
  const maxV = Math.max(...vals, 1)
  radarChart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: '#323e4c',
      borderColor: 'rgba(45,212,191,0.35)',
      textStyle: { color: '#f1f5fb', fontSize: 12 },
      formatter: (p) => {
        const i = p.dataIndex ?? 0
        const g = gasGrid.value[i]
        return `${g?.label || ''}: ${g?.value ?? '—'} μL/L`
      },
    },
    radar: {
      indicator: GAS_GRID.map((g) => ({ name: g.label, max: maxV })),
      center: ['50%', '52%'],
      radius: '62%',
      axisName: { color: '#9aa8bc', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' },
      splitArea: {
        areaStyle: {
          color: ['rgba(45,212,191,0.03)', 'rgba(45,212,191,0.07)'],
        },
      },
      axisLine: { lineStyle: { color: 'rgba(160,174,192,0.25)' } },
      splitLine: { lineStyle: { color: 'rgba(160,174,192,0.2)' } },
    },
    series: [{
      type: 'radar',
      data: [{
        value: vals,
        name: '含量',
        areaStyle: { color: 'rgba(59,130,246,0.28)' },
        lineStyle: { color: '#60a5fa', width: 2 },
        itemStyle: { color: '#93c5fd' },
      }],
    }],
  }, true)
}

function disposeRadar() {
  if (radarChart) {
    radarChart.dispose()
    radarChart = null
  }
}

async function loadSeries() {
  const res = await http.get('/diagnose/series')
  series.value = res.series || []
  summary.value = res.summary || {}
  const q = typeof route.query.date === 'string' ? route.query.date : ''
  const fallback = res.summary?.default_date || series.value.at(-1)?.date
  selectedDate.value = (q && series.value.some((s) => s.date === q)) ? q : fallback
}
async function loadDay(date) {
  if (!date) return
  const req = date
  dayLoading.value = true
  try {
    const data = await http.get(`/diagnose/day/${date}`)
    if (selectedDate.value !== req) return
    detail.value = data
    await nextTick()
    if (triggered.value) renderRadar()
    else disposeRadar()
  } finally {
    if (selectedDate.value === req) dayLoading.value = false
  }
}

watch(selectedDate, (d) => loadDay(d))
watch(
  () => route.query.date,
  (q) => {
    if (typeof q === 'string' && q && series.value.some((s) => s.date === q) && selectedDate.value !== q) {
      selectedDate.value = q
    }
  },
)
onMounted(async () => {
  try { await loadSeries() } finally { loading.value = false }
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  disposeRadar()
})
function onResize() {
  radarChart?.resize()
}
</script>

<template>
  <div v-loading="loading" class="diag">
    <div class="gp">
      <div class="gp-head">
        选择监测日
        <StdCite ref-id="722-10.3" label="DL/T 722-2014 判断故障的步骤" />
      </div>
      <div class="gp-body toolbar">
        <div class="nav">
          <button type="button" class="btn btn-ghost" :disabled="idx <= 0" @click="stepDay(-1)">‹ 前日</button>
          <el-date-picker
            v-model="selectedDate"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            :disabled-date="disabledDate"
            :cell-class-name="cellClassName"
            popper-class="dga-cal-popper"
            class="date-pick"
          />
          <button type="button" class="btn btn-ghost" :disabled="idx < 0 || idx >= series.length - 1" @click="stepDay(1)">后日 ›</button>
          <div class="cal-legend" aria-label="日历色标">
            <span><i class="lg alarm" />告警</span>
            <span><i class="lg w2" />注意2</span>
            <span><i class="lg w1" />注意1</span>
            <span><i class="lg normal" />正常</span>
            <span><i class="lg pre" />涨势预警</span>
          </div>
        </div>
        <div class="status">
          <span class="pill" :class="gradeClass(detail?.grade || current?.grade)">
            <i class="d" />{{ detail?.grade || current?.grade || '—' }}
          </span>
          <span v-if="detail?.is_pre || current?.is_pre" class="pill pre-pill">涨势预警</span>
          <span class="meta mono">{{ selectedDate }}</span>
        </div>
      </div>
    </div>

    <div v-loading="dayLoading" class="body">
      <template v-if="detail && !triggered">
        <div class="idle-banner">
          <div>
            <div class="idle-title">当日不做故障类型判断</div>
            <p>
              当前档位「{{ detail.grade }}」。进判型须满足其一：
              <strong>注意值2 / 告警</strong>，或
              <strong>总烃月环比超注意</strong>（含涨势预警）。
              依据见
              <StdCite inline ref-id="722-10.3" label="§10.3" /> /
              <StdCite inline ref-id="722-10.2.4a" label="§10.2.4 a" />。
              可用上方日期换一天查看。
            </p>
          </div>
        </div>
      </template>

      <template v-else-if="detail && triggered && !fusion">
        <div class="idle-banner">
          <div>
            <div class="idle-title">已触发判型，但融合结论缺失</div>
            <p>{{ diagnosis?.reason || diagnosis?.trigger_note || '请换日重试或检查算法输出' }}</p>
          </div>
        </div>
      </template>

      <template v-else-if="detail && triggered && fusion">
        <!-- 共用输入：三种方法都基于当日同一组含量 -->
        <section class="gp sample">
          <div class="gp-head">
            当日监测样含量
            <span class="head-ref">μL/L · 7 种特征气体 · 三比值 / 大卫三角 / 特征气体共用</span>
          </div>
          <div class="gp-body sample-body">
            <div class="trigger-bar">
              <span class="trigger-k">为何判型</span>
              <span
                class="trigger-note"
                :class="diagnosis?.trigger_by === 'rate' ? 'pre-tone' : gradeClass(detail.grade)"
              >
                {{ diagnosis?.trigger_note || '已触发' }}
              </span>
              <StdCite
                v-if="diagnosis?.trigger_by === 'rate'"
                inline
                ref-id="722-10.3"
                label="§10.3"
              />
              <StdCite
                v-else
                inline
                ref-id="1498-表A3"
                label="表A.3"
              />
            </div>
            <div class="gas-grid shared">
              <div v-for="g in gasGrid" :key="g.key" class="gas-cell" :class="{ hot: g.hot }">
                <span class="g-lab">{{ g.label }}</span>
                <span class="g-val mono">{{ g.value == null ? '—' : g.value }}</span>
                <span class="g-unit">μL/L</span>
              </div>
            </div>
            <p class="gas-src-hint">
              含量取自 {{ selectedDate }} 当日监测值；
              <span class="hint-hot">标红</span>
              表示特征气体法认为该组分偏高（工程门槛，非表5数值；亦不是分级档位颜色）。
            </p>
          </div>
        </section>

        <!-- 三种方法 -->
        <section class="methods">
          <!-- ① 三比值 -->
          <article class="method">
            <header class="method-head">
              <h3>三比值法</h3>
              <StdCite inline ref-id="722-表6-7" label="DL/T 722 §10.2 · 表6 → 表7" />
            </header>

            <table v-if="ratioRows.length" class="ratio-table">
              <thead>
                <tr>
                  <th>比值</th>
                  <th>计算值</th>
                  <th>编码</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in ratioRows" :key="row.key">
                  <td>
                    <div class="r-name">{{ row.label }}</div>
                    <div class="r-sub">{{ row.sub }}</div>
                  </td>
                  <td class="mono">{{ row.value }}</td>
                  <td><span class="code-pill" :class="codeTone(row.code)">{{ row.code }}</span></td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted">{{ ratios?.reason || '未判定' }}</p>

            <div v-if="ratios?.ok && ratios.code" class="combo">
              <span class="combo-label">比值组合编码</span>
              <div class="combo-boxes">
                <span v-for="(c, i) in ratios.code" :key="i" class="combo-box" :class="codeTone(c)">{{ c }}</span>
              </div>
            </div>

            <div class="verdict" :class="ratios?.ok ? 'hot' : ''">
              <span class="verdict-k">故障类型</span>
              {{ ratios?.ok ? (ratios.duval_code ? `${ratios.duval_code} · ${ratios.fault}` : ratios.fault) : (ratios?.fault || '—') }}
            </div>
          </article>

          <!-- ② 大卫三角 -->
          <article class="method">
            <header class="method-head">
              <h3>大卫三角形</h3>
              <StdCite inline ref-id="722-附录C" label="DL/T 722 附录C · 图C.2" />
            </header>

            <div class="zone-legend" title="附录C 六分区具体类型">
              <span v-for="z in ZONE_LEGEND" :key="z.id" class="zl">
                <i :style="{ background: z.color }" />
                <b>{{ z.id }}</b>
                <em>{{ z.name }}</em>
              </span>
            </div>

            <div class="duval-wrap">
              <svg v-if="duval?.ok" viewBox="0 0 400 360" class="duval-svg">
                <polygon v-for="z in ZONES" :key="z.id" :points="poly(z.verts)" :fill="z.fill"
                  stroke="rgba(160,174,192,0.2)" stroke-width="0.8" />
                <polygon :points="`${TOP.x},${TOP.y} ${RIGHT.x},${RIGHT.y} ${LEFT.x},${LEFT.y}`"
                  fill="none" stroke="rgba(200,210,230,0.75)" stroke-width="1.8" />
                <text v-for="z in ZONES" :key="z.id+'t'"
                  :x="labelPos(z.label).x" :y="labelPos(z.label).y" class="zlab">{{ z.text }}</text>
                <text :x="TOP.x" :y="TOP.y - 10" class="vertex">CH₄</text>
                <text :x="LEFT.x - 4" :y="LEFT.y + 16" class="vertex">C₂H₂</text>
                <text :x="RIGHT.x + 4" :y="RIGHT.y + 16" class="vertex">C₂H₄</text>
                <circle v-if="point" :cx="point.x" :cy="point.y" r="7"
                  fill="#f5555a" stroke="#fff" stroke-width="2" />
              </svg>
              <p v-else class="muted">{{ duval?.reason || duval?.fault || '未判定' }}</p>
            </div>

            <p v-if="duval?.percents" class="duval-coords mono">
              三角坐标取 CH₄ / C₂H₄ / C₂H₂ 归一化
              （{{ duval.percents.pct_ch4 }}% / {{ duval.percents.pct_c2h4 }}% / {{ duval.percents.pct_c2h2 }}%）
            </p>

            <div class="verdict" :class="duval?.ok ? 'hot' : ''">
              <span class="verdict-k">故障类型</span>
              {{ duval?.ok ? `${duval.zone} · ${duval.fault}` : (duval?.fault || '—') }}
            </div>
          </article>

          <!-- ③ 特征气体 -->
          <article class="method">
            <header class="method-head">
              <h3>特征气体法</h3>
              <StdCite inline ref-id="722-表5" label="DL/T 722 §10.1 · 表5" />
            </header>

            <div ref="radarEl" class="radar" />

            <div v-if="keyGas?.note" class="step-bar">
              <span class="step-k">表5 判据</span>
              {{ keyGas.note }}
            </div>
            <p v-if="keyGas?.ok" class="method-impl-note">
              {{ keyGas.impl_note || '表5定性匹配;偏高门槛与加权得分为本系统工程实现,非国标数值' }}
            </p>

            <div class="verdict" :class="keyGas?.ok ? 'hot' : ''">
              <span class="verdict-k">故障类型</span>
              {{ keyGas?.fault || '—' }}
            </div>
          </article>
        </section>
        <!-- 研判链路 + 综合结论（去重：左依表，右结论） -->
        <section class="gp conclude">
          <div class="gp-head">
            研判结论
            <span class="head-ref">可信度低 = 暂定 · 试验只核实</span>
          </div>
          <div class="gp-body conclude-body">
            <div class="conclude-col chain-col">
              <div class="col-title">依据</div>
              <ol class="reason-chain">
                <li v-for="(s, i) in reasoningSteps" :key="i">
                  <div class="rc-top">
                    <span class="rc-idx">{{ i + 1 }}</span>
                    <span class="rc-label">{{ s.label }}</span>
                    <StdCite v-if="s.cite" :ref-id="s.cite" :label="s.cite" inline />
                  </div>
                  <p class="rc-text">{{ s.text }}</p>
                </li>
              </ol>
            </div>

            <div class="conclude-col center">
              <div class="col-title">结论</div>
              <div class="judge" :class="isProvisional ? 'warn' : (consistencyOk ? 'ok' : 'warn')">
                <div class="judge-mark">{{ isProvisional ? '!' : (consistencyOk ? '✓' : '!') }}</div>
                <div class="judge-text">
                  {{ isProvisional ? '暂定 · 可信度低' : consistencyLabel }}
                </div>
              </div>
              <div class="judge-conf">
                <strong>{{ heroTitle }}</strong>
                <span class="conf-tag" :class="confidenceClass">{{ fusion.confidence }}</span>
              </div>
              <p class="judge-sum">{{ fusion.confidence_reason }}</p>
              <p v-if="fusion.paper_note" class="paper-note">{{ fusion.paper_note }}</p>
              <p v-if="isProvisional" class="warn-line">可信度低 · 暂定，不作确诊。</p>
              <p v-if="diagnosis.low_concentration" class="warn-line">§10.2.4 c 低浓度，比值慎用。</p>
            </div>
          </div>
        </section>

        <!-- 方案2：判型页只留对表钩子，清单在 Agent -->
        <section v-if="fusion" class="gp measures-hook" :class="{ verify: measuresPurpose === 'verify' }">
          <div class="gp-body hook-body">
            <p class="hook-text">
              {{ measuresHook }}
              <StdCite ref-id="722-附录D" label="722-附录D" inline />
              <StdCite
                v-if="(fusion.measures_1685_items || []).length || (fusion.measures_1685 || []).length"
                ref-id="1685-附录B"
                label="1685-附录B"
                inline
              />
            </p>
            <button type="button" class="btn btn-primary" @click="goAgentTrials">
              去分析编排查看其他检查性试验
            </button>
          </div>
        </section>

      </template>
    </div>
  </div>
</template>

<style scoped>
.diag { display: flex; flex-direction: column; gap: 12px; min-height: 200px; }

.toolbar { display: flex; flex-wrap: wrap; gap: 14px 20px; align-items: center; }
.nav { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.date-pick { width: 160px; }
.cal-legend {
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px;
  margin-left: 4px;
  font-size: 11px; color: var(--fg-4); font-weight: 600;
}
.cal-legend .lg {
  display: inline-block; width: 8px; height: 8px; border-radius: 50%;
  margin-right: 4px; vertical-align: 0;
}
.cal-legend .lg.alarm { background: #f87171; }
.cal-legend .lg.w2 { background: #fb923c; }
.cal-legend .lg.w1 { background: #fbbf24; }
.cal-legend .lg.normal { background: var(--lv-normal); }
.cal-legend .lg.pre { background: var(--lv-pre); }
.status { display: flex; align-items: center; gap: 10px; margin-left: auto; }
.meta { font-size: 12px; color: var(--fg-3); }
.pre-pill {
  font-size: 12px; font-weight: 700; padding: 3px 10px; border-radius: 999px;
}

.body { display: flex; flex-direction: column; gap: 12px; min-height: 120px; }

.idle-banner {
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  padding: 16px 18px; border-radius: var(--r);
  background: var(--bg-3); border: 1px solid var(--line); border-left: 3px solid var(--blue);
}
.idle-title { font-size: 14px; font-weight: 650; margin-bottom: 4px; }
.idle-banner p { margin: 0; font-size: 12.5px; color: var(--fg-3); line-height: 1.65; max-width: 640px; }

.methods {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  align-items: stretch;
}
@media (max-width: 1100px) {
  .methods { grid-template-columns: 1fr; }
}

.method {
  display: flex; flex-direction: column; gap: 10px;
  padding: 14px 14px 12px;
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  background: var(--bg-2);
  min-height: 100%;
}
.method-head {
  display: flex;
  flex-wrap: nowrap;
  align-items: baseline;
  gap: 8px 10px;
  min-width: 0;
}
.method-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 750;
  color: var(--fg);
  white-space: nowrap;
  flex-shrink: 0;
}
.method-head :deep(.std-cite-wrap) {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
.method-head :deep(.std-cite) {
  font-size: 10.5px;
}

/* 三比值表 */
.ratio-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.ratio-table th {
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: var(--fg-4);
  padding: 6px 8px;
  border-bottom: 1px solid var(--line);
}
.ratio-table td {
  padding: 9px 8px;
  border-bottom: 1px solid rgba(160,174,192,0.1);
  vertical-align: middle;
  color: var(--fg-2);
}
.ratio-table tr:last-child td { border-bottom: none; }
.r-name { font-weight: 650; color: var(--fg); font-family: 'JetBrains Mono', monospace; font-size: 12px; }
.r-sub { font-size: 10px; color: var(--fg-4); margin-top: 1px; }
.mono { font-family: 'JetBrains Mono', monospace; }

.code-pill {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 28px; height: 26px; padding: 0 8px;
  border-radius: 6px; font-weight: 800; font-size: 14px;
  font-family: 'JetBrains Mono', monospace;
}
.code-pill.c0 { background: rgba(52,211,153,0.18); color: #34d399; }
.code-pill.c1 { background: rgba(251,191,36,0.2); color: #fbbf24; }
.code-pill.c2 { background: rgba(245,85,90,0.22); color: #f87171; }

.combo {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  padding: 10px 12px; border-radius: 8px;
  background: var(--bg-3); border: 1px solid var(--line);
}
.combo-label { font-size: 11px; color: var(--fg-3); }
.combo-boxes { display: flex; gap: 6px; }
.combo-box {
  width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;
  border-radius: 8px; font-size: 18px; font-weight: 800;
  font-family: 'JetBrains Mono', monospace;
  border: 1px solid var(--line-2);
}
.combo-box.c0 { background: rgba(52,211,153,0.12); color: #34d399; }
.combo-box.c1 { background: rgba(251,191,36,0.14); color: #fbbf24; }
.combo-box.c2 { background: rgba(245,85,90,0.16); color: #f87171; }

.verdict {
  margin-top: auto;
  padding: 12px 14px;
  border-radius: 8px;
  font-size: 15px; font-weight: 800;
  text-align: center;
  background: var(--bg-3);
  color: var(--fg-2);
  border: 1px solid var(--line);
  line-height: 1.35;
  display: flex; flex-direction: column; gap: 4px; align-items: center;
}
.verdict-k {
  font-size: 10px; font-weight: 600; color: var(--fg-4);
  letter-spacing: 0.04em;
}
.verdict.hot {
  background: rgba(245,85,90,0.12);
  border-color: rgba(245,85,90,0.35);
  color: #fca5a5;
}
.verdict.hot .verdict-k { color: rgba(252,165,165,0.75); }

.method-impl-note {
  margin: 8px 0 0;
  font-size: 11px;
  line-height: 1.45;
  color: var(--fg-4);
}

/* 大卫三角 */
.zone-legend {
  display: flex; flex-wrap: nowrap; align-items: center;
  gap: 8px; overflow-x: auto; padding-bottom: 2px;
  font-size: 10px; color: var(--fg-3);
  -webkit-overflow-scrolling: touch;
}
.zl {
  display: inline-flex; align-items: center; gap: 3px;
  white-space: nowrap; flex-shrink: 0;
}
.zl i { width: 8px; height: 8px; border-radius: 2px; display: inline-block; flex-shrink: 0; }
.zl b {
  font-weight: 700; color: var(--fg-2);
  font-family: 'JetBrains Mono', monospace;
}
.zl em { font-style: normal; color: var(--fg-4); font-size: 9.5px; }

.duval-wrap {
  display: flex; justify-content: center; align-items: center;
  flex: 1; min-height: 200px;
}
.duval-svg { width: 100%; max-width: 280px; height: auto; }
.zlab {
  fill: var(--fg); font-size: 11px; font-weight: 700;
  text-anchor: middle; dominant-baseline: middle;
  font-family: 'JetBrains Mono', monospace;
}
.vertex {
  fill: var(--fg-3); font-size: 10px; font-weight: 600;
  text-anchor: middle;
  font-family: 'JetBrains Mono', monospace;
}
.duval-coords {
  margin: 0;
  font-size: 11px; color: var(--fg-3);
  text-align: center; line-height: 1.5;
}

/* 共用监测样 */
.head-ref {
  margin-left: auto;
  font-size: 10px;
  color: var(--fg-4);
  font-family: 'JetBrains Mono', monospace;
}
.sample-body { display: flex; flex-direction: column; gap: 8px; }
.gas-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 8px;
}
.gas-grid.shared .gas-cell {
  padding: 10px 12px;
  text-align: left;
}
.gas-grid.shared .g-val { font-size: 16px; }
.gas-cell {
  display: flex; flex-direction: column; gap: 2px;
  padding: 6px 4px; border-radius: 6px;
  background: var(--bg-3); border: 1px solid var(--line);
  min-width: 0;
}
.gas-cell.hot {
  border-color: rgba(245,85,90,0.45);
  background: rgba(245,85,90,0.1);
}
.g-lab { font-size: 10px; color: var(--fg-4); font-family: 'JetBrains Mono', monospace; }
.g-val {
  font-size: 13px; font-weight: 700; color: var(--fg);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.gas-cell.hot .g-val { color: #f87171; }
.g-unit { font-size: 9px; color: var(--fg-4); }
.gas-src-hint { margin: 0; font-size: 11px; color: var(--fg-4); line-height: 1.5; }
.gas-src-hint .hint-hot { color: #f87171; font-weight: 650; }
.trigger-bar {
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px;
  margin-bottom: 10px;
}
.trigger-k { font-size: 11px; color: var(--fg-4); font-weight: 650; flex-shrink: 0; }
.trigger-note {
  flex: 1 1 220px;
  font-size: 13px;
  font-weight: 650;
  line-height: 1.45;
  color: var(--fg-2);
}
.trigger-note.pre-tone { color: var(--lv-pre-2); }
.trigger-note.w1 { color: var(--lv-w1); }
.trigger-note.w2 { color: var(--lv-w2); }
.trigger-note.alarm { color: var(--lv-alarm); }
.pill.mini.pre-tone {
  background: var(--lv-pre-bg);
  border: 1px solid var(--lv-pre-line);
  color: var(--lv-pre-2);
}
.pill.mini.w2-tone {
  background: rgba(251, 146, 60, 0.12);
  border: 1px solid rgba(251, 146, 60, 0.4);
  color: #fdba74;
}

/* 特征气体 */
.radar { width: 100%; height: 220px; }
.step-bar {
  margin: 0; padding: 8px 10px; border-radius: 6px;
  font-size: 11.5px; color: var(--fg-2); line-height: 1.5;
  background: var(--bg-3); border: 1px solid var(--line);
}
.step-k {
  display: inline-block; margin-right: 6px;
  font-size: 10px; font-weight: 700; color: var(--amber);
}
.muted { margin: 0; font-size: 12px; color: var(--fg-4); }

/* 底栏：研判链路 + 综合结论 */
.conclude-body {
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  gap: 16px;
}
@media (max-width: 900px) {
  .conclude-body { grid-template-columns: 1fr; }
}
.col-title {
  font-size: 12px; font-weight: 700; color: var(--fg-3);
  margin-bottom: 10px;
}
.reason-chain {
  margin: 0; padding: 0; list-style: none;
  display: flex; flex-direction: column; gap: 10px;
}
.reason-chain li {
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--bg-3);
  border-left: 3px solid var(--amber);
}
.rc-top {
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px 8px;
  margin-bottom: 2px;
}
.rc-idx {
  width: 16px; height: 16px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: 800;
  background: rgba(251, 191, 36, 0.2); color: #fbbf24;
}
.rc-label { font-size: 12px; font-weight: 700; color: var(--fg); }
.rc-text {
  margin: 0; font-size: 12px; color: var(--fg-2); line-height: 1.45;
}
.cmp-mini { margin-top: 14px; text-align: left; }
.cmp { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 8px; }
.cmp li {
  display: flex; flex-direction: column; gap: 2px;
  padding: 8px 10px; border-radius: 8px; background: var(--bg-3);
  font-size: 11.5px; color: var(--fg-3);
}
.cmp strong { font-size: 13px; color: var(--fg); font-weight: 700; }

.conclude-col.center { text-align: center; }
.conclude-col.chain-col { text-align: left; }
.judge { margin-bottom: 8px; }
.judge-mark {
  width: 44px; height: 44px; margin: 0 auto 6px;
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 20px; font-weight: 800;
}
.judge.ok .judge-mark { background: rgba(52,211,153,0.18); color: #34d399; }
.judge.warn .judge-mark { background: rgba(251,191,36,0.18); color: #fbbf24; }
.judge-text { font-size: 16px; font-weight: 800; color: var(--fg); }
.judge-conf {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 8px;
  margin-top: 8px; font-size: 12.5px; color: var(--fg-2);
}
.judge-conf .conf-role { font-size: 11px; color: var(--fg-4); font-weight: 650; }
.judge-conf strong { color: var(--amber-2); font-size: 14px; }
.judge-sum {
  margin: 8px 0 0; font-size: 12px; color: var(--fg-3);
  line-height: 1.45; text-align: center;
}
.paper-note {
  margin: 6px 0 0; font-size: 12px; color: var(--lv-w2);
  line-height: 1.45; text-align: center;
}
.conf-tag {
  font-size: 11px; font-weight: 700; padding: 3px 9px; border-radius: 20px;
}
.conf-tag.high { background: var(--lv-normal-bg); color: var(--lv-normal); }
.conf-tag.mid { background: var(--lv-w1-bg); color: var(--lv-w1); }
.conf-tag.low { background: var(--lv-alarm-bg); color: var(--lv-alarm); }

.warn-line {
  margin: 6px 0 0; font-size: 11.5px;
  color: var(--lv-w2) !important; line-height: 1.4;
  text-align: center;
}

.measures-hook.verify {
  border-color: rgba(251, 191, 36, 0.35);
}
.hook-body {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
  gap: 12px 16px;
}
.hook-text {
  margin: 0; flex: 1; min-width: 220px;
  font-size: 12.5px; color: var(--fg-2); line-height: 1.5;
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px 8px;
}

.toolbar :deep(.el-input__wrapper),
.toolbar :deep(.el-select__wrapper) {
  background: var(--bg-3) !important;
  box-shadow: 0 0 0 1px var(--line-2) inset !important;
}
.toolbar :deep(.el-input__inner),
.toolbar :deep(.el-select__selected-item) { color: var(--fg) !important; }
</style>
