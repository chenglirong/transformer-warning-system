<script setup>
// 故障判型页 —— 三方法对标参考页信息密度:
// 三比值表+编码块 / 大卫三角图 / 特征气体主次气条形 → 一致性结论
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
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
  s += '。其他检查性试验清单见 Agent 分析。'
  return s
})

function goAgentTrials() {
  router.push({ name: 'agent', query: selectedDate.value ? { date: selectedDate.value } : {} })
}

/** 研判链路：进入门槛 + 三法依表；辅助比值改到右侧专区，避免左右重复 */
const AUX_LABELS = new Set(['CO₂/CO', 'C₂H₂/H₂', 'O₂/N₂'])

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
    const core = f.reasoning.filter((s) => !AUX_LABELS.has(s.label))
    return [...head, ...core]
  }
  const steps = [...head]
  methodResults.value.forEach((m, i) => {
    const cites = ['722-表6-7', '722-附录C', '722-表5']
    steps.push({ label: m.name, text: m.value, cite: cites[i] })
  })
  return steps
})

/** §10.2.3 辅助比值：alert + info 都展示；3~7 等无 note 的正常区间不占版 */
const AUX_RATIO_META = [
  { key: 'co2_co', label: 'CO₂/CO', cite: '722-10.2.3.1', band: '3~7 正常' },
  { key: 'c2h2_h2', label: 'C₂H₂/H₂', cite: '722-10.2.3.2', band: '≤2 正常' },
  { key: 'o2_n2', label: 'O₂/N₂', cite: '722-10.2.3.3', band: '≥0.3 正常' },
]

const auxPack = computed(() => {
  const a = fusion.value?.aux_ratios
  if (!a) return null
  const byLabel = Object.fromEntries((a.notes || []).map((n) => [n.ratio, n]))
  const rows = AUX_RATIO_META.map((m) => {
    const value = a[m.key]
    const note = byLabel[m.label] || null
    return {
      ...m,
      value: value == null ? null : value,
      level: note?.level || null,
      text: note?.text || null,
    }
  }).filter((r) => r.text)
  if (!rows.length) return null
  return {
    rows,
    hasAlert: rows.some((r) => r.level === 'alert'),
  }
})

/** DL/T 722 表3 单项注意值(220kV 及以下):只有 H₂、C₂H₂ 有单项值;总烃(四烃合计)单列 */
const TABLE3_ATTENTION = { h2: 150, c2h2: 5 }
const TABLE3_THC = 150

/** 只对有表3单项注意值的气标红(CH₄/C₂H₄/C₂H₆ 无单项值,不因总烃连坐) */
function gasExceedsTable3(key, value) {
  if (value == null || Number.isNaN(value)) return false
  const v = Number(value)
  if (key === 'h2') return v >= TABLE3_ATTENTION.h2
  if (key === 'c2h2') return v >= TABLE3_ATTENTION.c2h2
  return false
}

const GAS_GRID = [
  { key: 'h2', label: 'H₂' },
  { key: 'ch4', label: 'CH₄' },
  { key: 'c2h2', label: 'C₂H₂' },
  { key: 'c2h4', label: 'C₂H₄' },
  { key: 'c2h6', label: 'C₂H₆' },
  { key: 'co', label: 'CO' },
  { key: 'co2', label: 'CO₂' },
]

// 本次命中表5行的主气/次气(后端 key_gas 返回)
const GAS_LABEL = Object.fromEntries(GAS_GRID.map((g) => [g.key, g.label]))
/** 把气体键名数组 → {key,label,value} 数组(带当日实测值) */
function gasRow(keys) {
  const g = detail.value?.gases || {}
  return (keys || []).map((k) => {
    let raw = g[k]
    if (k === 'co') raw = detail.value?.co ?? raw
    if (k === 'co2') raw = detail.value?.co2 ?? raw
    return { key: k, label: GAS_LABEL[k] || k, value: raw == null ? null : Number(raw) }
  })
}
const keyGasPrimaryRows = computed(() => gasRow(keyGas.value?.primary))
const keyGasSecondaryRows = computed(() => gasRow(keyGas.value?.secondary))
// 命中行主+次气条形:长度相对本组最大值
const keyGasBars = computed(() => {
  const rows = [
    ...keyGasPrimaryRows.value.map((r) => ({ ...r, role: 'primary' })),
    ...keyGasSecondaryRows.value.map((r) => ({ ...r, role: 'secondary' })),
  ]
  const maxV = Math.max(1, ...rows.map((r) => (r.value != null && r.value > 0 ? r.value : 0)))
  return rows.map((r) => ({
    ...r,
    pct: r.value != null && r.value > 0 ? Math.max(4, (r.value / maxV) * 100) : 0,
  }))
})
// 表5 落选行(非采用行),带落选原因,供「为什么不是它」对照
const keyGasRejected = computed(() =>
  (keyGas.value?.rows || []).filter((r) => !r.chosen).map((r) => ({
    fault: r.fault,
    reject: r.reject || (r.matched ? '同样命中,但特征气体不如采用行齐全' : ''),
    matched: r.matched,
  })),
)

const gasThc = computed(() => {
  const g = detail.value?.gases || {}
  return ['ch4', 'c2h4', 'c2h6', 'c2h2'].reduce((s, k) => {
    const v = g[k]
    return s + (v == null || Number.isNaN(v) ? 0 : Number(v))
  }, 0)
})
const gasGrid = computed(() => {
  const g = detail.value?.gases || {}
  return GAS_GRID.map((row) => {
    let raw = g[row.key]
    if (row.key === 'co') raw = detail.value?.co ?? raw
    if (row.key === 'co2') raw = detail.value?.co2 ?? raw
    const value = raw == null ? null : Number(raw)
    return {
      ...row,
      value,
      hot: gasExceedsTable3(row.key, value),
    }
  })
})

// —— Duval ——
// 三角三顶点像素坐标(留出四周页边,给 CH₄/C₂H₂/C₂H₄ 轴标注让位)
const TOP = { x: 200, y: 46 }
const LEFT = { x: 46, y: 320 }
const RIGHT = { x: 354, y: 320 }

/** 三坐标 → SVG/画布像素点(重心插值)。返回 {x, y}。 */
function triXY(c2h2, c2h4, ch4) {
  const s = c2h2 + c2h4 + ch4
  const a = c2h2 / s, b = c2h4 / s, c = ch4 / s
  return {
    x: a * LEFT.x + b * RIGHT.x + c * TOP.x,
    y: a * LEFT.y + b * RIGHT.y + c * TOP.y,
  }
}
// 大卫三角:改用离屏 Canvas 逐像素上色,着色规则 == 后端 classify_zone,
// 图区与落区判定永远一致(不再手连顶点,免接缝/漏叠)。边界照 DL/T 722—2014 表C.1。
// 各区颜色沿用页面图例 ZONE_LEGEND。
const ZONE_COLORS = {
  PD: '#60a5fa', D1: '#34d399', D2: '#f5555a',
  T1: '#facc15', T2: '#fb923c', T3: '#a78bfa', DT: '#2dd4bf',
}

// 与后端 diagnose/duval.py 的 classify_zone 逐行对应(严格照 DL/T 722—2014 表C.1《区域极限》)。
// D2 = 四条极限线 23%C2H4 / 13%C2H2 / 38%C2H4 / 29%C2H2 围出的四边形。
// 边界点归更严重区(严重度 D2>D1>D+T>T3>T2>T1):
//   C2H2=13/29→D类/D2  C2H4=23/38→D2  C2H2=4/15→D+T  C2H4=10/50→T2/T3
//   唯 PD(CH4=98)按行业习惯取 ≥98(含线)。
function classifyZone(pctCh4, pctC2h4, pctC2h2) {
  if (pctCh4 >= 98) return 'PD'
  if (pctC2h2 < 4) {
    if (pctC2h4 < 10) return 'T1'
    if (pctC2h4 < 50) return 'T2'
    return 'T3'
  }
  if (pctC2h2 < 15 && pctC2h4 >= 50) return 'T3'
  if (pctC2h2 >= 13) {
    if (pctC2h4 < 23) return 'D1'
    if (pctC2h4 <= 38 || pctC2h2 >= 29) return 'D2'
    return 'DT'  // C2H2 13~29% 且 C2H4>38% 的右上折块 → D+T
  }
  return 'DT'    // 4%≤C2H2<13% 且非 T3:放电兼过热夹区
}

// 三条边的刻度(20/40/60/80),照国标图C.2:每边一组短刻度线 + 数字
// 每条边由「起点顶点 → 终点顶点」,frac=沿边比例(该边终点组分的百分比)
const AXIS_TICKS = [20, 40, 60, 80]
function edgeTicks(A, B, outN) {
  // A→B 边,outN=垂直边向外的法向(单位化后偏移)。返回刻度线段与数字位置。
  const dx = B.x - A.x, dy = B.y - A.y
  const len = Math.hypot(dx, dy)
  const nx = outN.x, ny = outN.y
  return AXIS_TICKS.map((t) => {
    const f = t / 100
    const x = A.x + dx * f, y = A.y + dy * f
    return {
      t,
      x1: x, y1: y,
      x2: x + nx * 6, y2: y + ny * 6,
      tx: x + nx * 15, ty: y + ny * 15,
    }
  })
}
// 三条边外法向(粗略指向三角外侧)
const leftAxis = computed(() => edgeTicks(LEFT, TOP, { x: -0.87, y: -0.5 }))   // C2H2→CH4 腰(%CH4 递增)
const rightAxis = computed(() => edgeTicks(TOP, RIGHT, { x: 0.87, y: -0.5 }))  // CH4→C2H4 腰(%C2H4 递增)
const bottomAxis = computed(() => edgeTicks(RIGHT, LEFT, { x: 0, y: 1 }))      // C2H4→C2H2 底(%C2H2 递增)

// PD/T1/T2 三区太窄,标注引出到右腰外(照国标图C.2:引线从区内指向腰外文字)。
// from=区内锚点 [C2H2,C2H4,CH4],to=腰外文字像素点。
function leader(fromTri, toPx) {
  const p = triXY(fromTri[0], fromTri[1], fromTri[2])
  return { x1: p.x, y1: p.y, x2: toPx.x, y2: toPx.y, tx: toPx.x, ty: toPx.y }
}
const pdLeader = computed(() => leader([0.5, 0.5, 99], { x: TOP.x, y: TOP.y - 22 }))
const t1Leader = computed(() => leader([2, 6, 92], { x: TOP.x + 60, y: TOP.y + 4 }))
const t2Leader = computed(() => leader([2.5, 24, 73.5], { x: TOP.x + 96, y: TOP.y + 42 }))

// 区内文字锚点 [C2H2%, C2H4%, CH4%]。PD/T1/T2 太窄改用引线,不进此表。
const ZONE_LABELS_POS = [
  { id: 'T3', text: 'T3', at: [8, 82, 10] },
  { id: 'D1', text: 'D1', at: [55, 10, 35] },
  { id: 'D2', text: 'D2', at: [40, 28, 32] },
  { id: 'DT', text: 'D+T', at: [20, 48, 32] },
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
  return triXY(p.pct_c2h2, p.pct_c2h4, p.pct_ch4)
})
const labelPos = (v) => triXY(v[0], v[1], v[2])

// 判定某像素是否落在三角内(重心系数全 ≥0)。
function pxToTri(px, py) {
  // 解重心坐标:px,py = a*LEFT + b*RIGHT + c*TOP, a+b+c=1
  const det = (RIGHT.x - LEFT.x) * (TOP.y - LEFT.y) - (TOP.x - LEFT.x) * (RIGHT.y - LEFT.y)
  const b = ((px - LEFT.x) * (TOP.y - LEFT.y) - (TOP.x - LEFT.x) * (py - LEFT.y)) / det
  const c = ((RIGHT.x - LEFT.x) * (py - LEFT.y) - (px - LEFT.x) * (RIGHT.y - LEFT.y)) / det
  const a = 1 - b - c
  if (a < -1e-9 || b < -1e-9 || c < -1e-9) return null
  // a=C2H2占比 b=C2H4 c=CH4
  return { c2h2: a * 100, c2h4: b * 100, ch4: c * 100 }
}

const duvalCanvas = ref(null)
/** 逐像素按 classifyZone 上色,着色规则 == 后端落区。 */
function drawDuval() {
  const cv = duvalCanvas.value
  if (!cv) return
  const W = 400, H = 360
  const dpr = window.devicePixelRatio || 1
  cv.width = W * dpr
  cv.height = H * dpr
  const ctx = cv.getContext('2d')
  ctx.scale(dpr, dpr)
  ctx.clearRect(0, 0, W, H)
  const img = ctx.createImageData(W * dpr, H * dpr)
  const data = img.data
  const hexToRgb = (h) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]
  const rgbCache = {}
  for (const [id, hex] of Object.entries(ZONE_COLORS)) rgbCache[id] = hexToRgb(hex)
  for (let py = 0; py < H * dpr; py++) {
    for (let px = 0; px < W * dpr; px++) {
      const tri = pxToTri(px / dpr, py / dpr)
      const off = (py * W * dpr + px) * 4
      if (!tri) { data[off + 3] = 0; continue }
      const z = classifyZone(tri.ch4, tri.c2h4, tri.c2h2)
      const [r, g, b] = rgbCache[z]
      data[off] = r; data[off + 1] = g; data[off + 2] = b
      data[off + 3] = 128 // ~0.5 alpha,和原 fill 透明度相近
    }
  }
  ctx.putImageData(img, 0, 0)
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

async function loadSeries() {
  const res = await http.get('/detect/series')
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
    if (duval.value?.ok) drawDuval()
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
})
function onResize() {
  if (duval.value?.ok) drawDuval()
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
            <div class="idle-title">当日不做故障判型</div>
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
            <div class="idle-title">已触发判型，但交叉研判结论缺失</div>
            <p>{{ diagnosis?.reason || diagnosis?.trigger_note || '请换日重试或检查算法输出' }}</p>
          </div>
        </div>
      </template>

      <template v-else-if="detail && triggered && fusion">
        <!-- 共用输入：三种方法都基于当日同一组含量 -->
        <section class="gp sample">
          <div class="gp-head">
            当日监测样含量
            <span class="head-ref">μL/L</span>
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
                ref-id="722-表3"
                label="722 表3 注意值"
              />
            </div>
            <div class="gas-grid shared">
              <div v-for="g in gasGrid" :key="g.key" class="gas-cell" :class="{ hot: g.hot }">
                <span class="g-lab">{{ g.label }}</span>
                <span class="g-val mono">{{ g.value == null ? '—' : g.value }}</span>
                <span class="g-unit">μL/L</span>
              </div>
            </div>
            <div class="thc-row" :class="{ hot: gasThc >= 150 }">
              <span class="thc-lab">总烃合计（CH₄+C₂H₄+C₂H₆+C₂H₂）</span>
              <span class="thc-val mono">{{ gasThc.toFixed(2) }} μL/L</span>
              <StdCite inline ref-id="722-表3" label="722 表3 注意值 150" />
            </div>
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
              <div v-if="duval?.ok" class="duval-stage">
                <!-- 分区色块:离屏 Canvas 逐像素上色,规则 == 后端 classify_zone -->
                <canvas ref="duvalCanvas" class="duval-canvas" />
                <!-- 外框 / 顶点标注 / 分区文字 / 落点:SVG 叠在 canvas 之上 -->
                <svg viewBox="0 0 400 360" class="duval-svg duval-overlay">
                  <polygon :points="`${TOP.x},${TOP.y} ${RIGHT.x},${RIGHT.y} ${LEFT.x},${LEFT.y}`"
                    fill="none" stroke="rgba(200,210,230,0.75)" stroke-width="1.8" />

                  <!-- 三边刻度(20/40/60/80)+ 数字 -->
                  <g class="axis-ticks">
                    <template v-for="(tk, i) in leftAxis" :key="'l'+i">
                      <line :x1="tk.x1" :y1="tk.y1" :x2="tk.x2" :y2="tk.y2" />
                      <text :x="tk.tx" :y="tk.ty" class="tick-num">{{ tk.t }}</text>
                    </template>
                    <template v-for="(tk, i) in rightAxis" :key="'r'+i">
                      <line :x1="tk.x1" :y1="tk.y1" :x2="tk.x2" :y2="tk.y2" />
                      <text :x="tk.tx" :y="tk.ty" class="tick-num">{{ tk.t }}</text>
                    </template>
                    <template v-for="(tk, i) in bottomAxis" :key="'b'+i">
                      <line :x1="tk.x1" :y1="tk.y1" :x2="tk.x2" :y2="tk.y2" />
                      <text :x="tk.tx" :y="tk.ty" class="tick-num">{{ tk.t }}</text>
                    </template>
                  </g>

                  <!-- 区内文字(PD 除外) -->
                  <text v-for="z in ZONE_LABELS_POS" :key="z.id+'t'"
                    :x="labelPos(z.at).x" :y="labelPos(z.at).y" class="zlab">{{ z.text }}</text>

                  <!-- PD / T1 / T2 太窄,引线指出,标注在腰外(照国标图C.2) -->
                  <g class="leaders">
                    <line :x1="pdLeader.x1" :y1="pdLeader.y1" :x2="pdLeader.x2" :y2="pdLeader.y2" />
                    <text :x="pdLeader.tx" :y="pdLeader.ty - 4" class="zlab">PD</text>
                    <line :x1="t1Leader.x1" :y1="t1Leader.y1" :x2="t1Leader.x2" :y2="t1Leader.y2" />
                    <text :x="t1Leader.tx + 4" :y="t1Leader.ty" class="zlab" text-anchor="start">T1</text>
                    <line :x1="t2Leader.x1" :y1="t2Leader.y1" :x2="t2Leader.x2" :y2="t2Leader.y2" />
                    <text :x="t2Leader.tx + 4" :y="t2Leader.ty" class="zlab" text-anchor="start">T2</text>
                  </g>

                  <!-- 轴名放三条边中点外侧(照国标图C.2) -->
                  <text :x="(TOP.x + LEFT.x) / 2 - 34" :y="(TOP.y + LEFT.y) / 2" class="vertex" text-anchor="middle">%CH₄</text>
                  <text :x="(TOP.x + RIGHT.x) / 2 + 34" :y="(TOP.y + RIGHT.y) / 2" class="vertex" text-anchor="middle">%C₂H₄</text>
                  <text :x="(LEFT.x + RIGHT.x) / 2" :y="LEFT.y + 34" class="vertex" text-anchor="middle">%C₂H₂</text>

                  <circle v-if="point" :cx="point.x" :cy="point.y" r="7"
                    fill="#f5555a" stroke="#fff" stroke-width="2" />
                </svg>
              </div>
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

            <div v-if="keyGas?.ok" class="kg-bars">
              <div v-for="x in keyGasBars" :key="x.key" class="kg-bar-row" :class="x.role">
                <span class="kg-bar-tag" :class="x.role">{{ x.role === 'primary' ? '主' : '次' }}</span>
                <span class="kg-bar-lab mono">{{ x.label }}</span>
                <div class="kg-bar-track">
                  <div class="kg-bar-fill" :class="x.role" :style="{ width: x.pct + '%' }" />
                </div>
                <span class="kg-bar-val mono">{{ x.value == null ? '—' : x.value }}</span>
              </div>
            </div>

            <p class="gas-src-hint kg-gas-hint">
              条形为该故障主/次要特征气体的当日浓度（μL/L）。
            </p>

            <div v-if="keyGas?.note" class="step-bar">
              <span class="step-k">表5 判据</span>
              {{ keyGas.note }}
            </div>

            <!-- 表5 其余行为何落选(命中行+落选行对照) -->
            <details v-if="keyGasRejected.length" class="kg-reject">
              <summary>表5 其余 {{ keyGasRejected.length }} 行为何未选？</summary>
              <ul>
                <li v-for="r in keyGasRejected" :key="r.fault">
                  <b>{{ r.fault }}</b><span class="kg-rj-why">{{ r.reject }}</span>
                </li>
              </ul>
            </details>

            <div class="verdict" :class="keyGas?.ok ? 'hot' : ''">
              <span class="verdict-k">故障类型</span>
              {{ keyGas?.fault || '—' }}
            </div>
          </article>
        </section>
        <!-- 研判链路 + 综合结论（去重：左依表，右结论）；辅助比值附于结论，不作第四方法卡 -->
        <section class="gp conclude">
          <div class="gp-head">
            研判结论
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
              <p v-if="fusion.paper_note" class="paper-note">
                <span class="paper-k">油/纸附注</span>
                {{ fusion.paper_note }}
              </p>

              <div v-if="auxPack" class="aux-box" :class="{ alert: auxPack.hasAlert, info: !auxPack.hasAlert }">
                <div class="aux-head">
                  <span class="aux-title">辅助比值</span>
                  <span class="aux-sub">DL/T 722</span>
                </div>
                <ul class="aux-rows">
                  <li v-for="r in auxPack.rows" :key="r.key" :class="r.level || 'idle'">
                    <div class="aux-top">
                      <span class="aux-lab">{{ r.label }}</span>
                      <span class="aux-val mono">{{ r.value == null ? '—' : r.value }}</span>
                      <span v-if="r.level === 'alert'" class="aux-tag alert">提示</span>
                      <span v-else-if="r.level === 'info'" class="aux-tag info">参考</span>
                      <span v-else class="aux-tag idle">{{ r.band }}</span>
                    </div>
                    <p v-if="r.text" class="aux-text">{{ r.text }}</p>
                  </li>
                </ul>
              </div>

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
              去 Agent 分析
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
.duval-stage { position: relative; width: 100%; max-width: 280px; }
.duval-canvas { display: block; width: 100%; height: auto; aspect-ratio: 400 / 360; }
.duval-overlay { position: absolute; inset: 0; width: 100%; height: 100%; }
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
.axis-ticks line { stroke: rgba(200, 210, 230, 0.55); stroke-width: 0.8; }
.leaders line { stroke: rgba(200, 210, 230, 0.6); stroke-width: 0.8; }
.tick-num {
  fill: var(--fg-4); font-size: 8px;
  text-anchor: middle; dominant-baseline: middle;
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
.thc-row {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  margin: 8px 0 4px; padding: 6px 10px; border-radius: 6px;
  background: var(--bg-3); border: 1px solid var(--line);
}
.thc-row.hot { border-color: rgba(245,85,90,0.45); background: rgba(245,85,90,0.1); }
.thc-lab { font-size: 11.5px; color: var(--fg-3); }
.thc-val { font-size: 13px; font-weight: 700; color: var(--fg); }
.thc-row.hot .thc-val { color: #f87171; }
.gas-src-hint { margin: 0; font-size: 11px; color: var(--fg-4); line-height: 1.5; }
.gas-src-hint .hint-hot { color: #f87171; font-weight: 650; }
.gas-src-hint .hint-aux { color: var(--teal, #2dd4bf); font-weight: 600; }
.kg-gas-hint { margin-top: 8px; }
.kg-bars { display: flex; flex-direction: column; gap: 7px; }
.kg-bar-row { display: flex; align-items: center; gap: 8px; }
.kg-bar-tag {
  flex-shrink: 0; width: 16px; height: 16px; border-radius: 4px;
  font-size: 10px; font-weight: 700; line-height: 16px; text-align: center;
}
.kg-bar-tag.primary { background: rgba(45,212,191,0.2); color: #2dd4bf; }
.kg-bar-tag.secondary { background: rgba(94,234,212,0.12); color: #5eead4; }
.kg-bar-lab { flex-shrink: 0; width: 3.2em; font-size: 12px; color: var(--fg-2); }
.kg-bar-track {
  flex: 1; height: 10px; border-radius: 5px;
  background: rgba(160,174,192,0.12); overflow: hidden;
}
.kg-bar-fill { height: 100%; border-radius: 5px; transition: width .3s ease; }
.kg-bar-fill.primary { background: #2dd4bf; }
.kg-bar-fill.secondary { background: rgba(94,234,212,0.6); }
.kg-bar-val {
  flex-shrink: 0; min-width: 5.5em; text-align: right;
  font-size: 11.5px; font-weight: 700; color: var(--fg);
}
.kg-reject { margin-top: 8px; font-size: 11px; }
.kg-reject summary {
  cursor: pointer; color: var(--fg-3); user-select: none;
  padding: 4px 0;
}
.kg-reject summary:hover { color: var(--fg-2); }
.kg-reject ul { margin: 4px 0 0; padding-left: 4px; list-style: none; display: flex; flex-direction: column; gap: 4px; }
.kg-reject li { color: var(--fg-3); line-height: 1.5; }
.kg-reject li b { color: var(--fg-2); font-weight: 650; margin-right: 6px; }
.kg-rj-why { color: var(--fg-4); }
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
  margin: 8px 0 0; font-size: 12px; color: var(--lv-w2);
  line-height: 1.45; text-align: left;
}
.paper-k {
  display: inline-block;
  margin-right: 6px;
  font-size: 10px;
  font-weight: 700;
  color: var(--fg-4);
  letter-spacing: 0.04em;
}
.conf-tag {
  font-size: 11px; font-weight: 700; padding: 3px 9px; border-radius: 20px;
}
.conf-tag.high { background: var(--lv-normal-bg); color: var(--lv-normal); }
.conf-tag.mid { background: var(--lv-w1-bg); color: var(--lv-w1); }
.conf-tag.low { background: var(--lv-alarm-bg); color: var(--lv-alarm); }

.aux-box {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: var(--bg-3);
  text-align: left;
}
.aux-box.alert {
  border-color: rgba(251, 191, 36, 0.35);
  background: rgba(251, 191, 36, 0.06);
}
.aux-box.info {
  border-color: rgba(52, 211, 153, 0.28);
  background: rgba(52, 211, 153, 0.05);
}
.aux-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 8px;
  margin-bottom: 8px;
}
.aux-title {
  font-size: 11px;
  font-weight: 700;
  color: var(--fg-2);
  letter-spacing: 0.04em;
}
.aux-sub {
  font-size: 10px;
  color: var(--fg-4);
}
.aux-rows {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.aux-top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 8px;
}
.aux-lab {
  font-size: 12px;
  font-weight: 700;
  color: var(--fg);
  font-family: 'JetBrains Mono', monospace;
  min-width: 4.5em;
}
.aux-val {
  font-size: 13px;
  font-weight: 700;
  color: var(--fg-2);
}
.aux-tag {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 999px;
}
.aux-tag.alert {
  background: rgba(251, 191, 36, 0.18);
  color: var(--lv-w1);
}
.aux-tag.info {
  background: var(--lv-normal-bg);
  color: var(--lv-normal);
}
.aux-tag.idle {
  background: var(--bg-2);
  color: var(--fg-4);
}
.aux-text {
  margin: 4px 0 0;
  font-size: 11.5px;
  line-height: 1.45;
  color: var(--fg-3);
}

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
