<script setup>
// 气体分级检测 —— 选单日；表A.3 七项各自报档（含正常）+ 当日最高档
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import http from '@/service/http'
import StdCite from '@/components/StdCite.vue'

const route = useRoute()
const loading = ref(true)
const loadError = ref('')
const series = ref([])
const summary = ref({})
const selectedDate = ref('')
const detail = ref(null)
const dayLoading = ref(false)
const dayError = ref('')

/** 卡片旁：气体符号 / 总烃写组成式（不写 THC） */
const CARD_META = {
  '绝对浓度|c2h2': { en: 'C₂H₂' },
  '绝对浓度|h2': { en: 'H₂' },
  '绝对浓度|total_hydrocarbon': { en: 'CH₄+C₂H₄+C₂H₆+C₂H₂' },
  '绝对增量|c2h2': { en: 'C₂H₂' },
  '绝对增量|h2': { en: 'H₂' },
  '绝对增量|total_hydrocarbon': { en: 'CH₄+C₂H₄+C₂H₆+C₂H₂' },
  '相对增长速率|total_hydrocarbon': { en: 'CH₄+C₂H₄+C₂H₆+C₂H₂' },
}

/** 式 A.1 / A.2 用 HTML 下标排版，与国标一致，不用截图 */
const BASIS_META = {
  绝对浓度: {
    title: '绝对浓度',
    unit: 'μL/L',
  },
  绝对增量: {
    title: '绝对增量',
    unit: 'μL/L·周',
    formula: 'a1',
  },
  相对增长速率: {
    title: '相对增长速率',
    unit: '%/周 · 仅总烃；参比 <30 μL/L 时不计算',
    formula: 'a2',
  },
}

const BASIS_ORDER = ['绝对浓度', '绝对增量', '相对增长速率']

const gradeClass = (g) => ({
  正常: 'normal', 注意值1: 'w1', 注意值2: 'w2', 告警值: 'alarm',
}[g] || 'normal')

const idx = computed(() => series.value.findIndex((s) => s.date === selectedDate.value))
const dateRange = computed(() => {
  if (!series.value.length) return null
  return [series.value[0].date, series.value[series.value.length - 1].date]
})

const dayGrade = computed(() => detail.value?.grade || null)
const isPre = computed(() => !!detail.value?.is_pre)
const rateRising = computed(() => !!detail.value?.rate_rising)
const thcRel = computed(() => detail.value?.thc_rel_rate)
const urgency = computed(() => detail.value?.urgency || null)

/** 右侧三格下方一句人话，给值班员看懂「这是啥、为啥是这个值」 */
const rateHint = computed(() => {
  const r = thcRel.value
  if (r == null) return '相对产气速率；总烃参比不足时暂不计'
  if (r >= 10) return '已超注意值约 10%/月'
  return '未超注意值约 10%/月'
})
const preHint = computed(() => {
  if (isPre.value) {
    return '含量档仍为正常/注意值1，但月环比已超注意值约 10%/月'
  }
  if (rateRising.value) {
    return '月环比已超，但当日档已达注意值2/告警 → 改看处置紧急度'
  }
  return '触发条件：档位仍为正常/注意值1，且月环比 ≥10%/月'
})
const urgencyLabel = computed(() => {
  if (urgency.value?.level) return urgency.value.level
  if (['注意值2', '告警值'].includes(dayGrade.value)) return '—'
  return '不适用'
})
const urgencyHint = computed(() => {
  if (urgency.value?.advice) return urgency.value.advice
  if (['注意值2', '告警值'].includes(dayGrade.value)) {
    return '已达注意值2/告警，正在研判急缓（涨势快→高，暂稳→中，仅H₂→低）'
  }
  return '仅注意值2/告警时才判急缓；当前档位更低，故不适用'
})

/** 抬到当日最高档的判据（可能多项并列） */
const maxDrivers = computed(() => {
  const list = detail.value?.indicators || []
  const g = dayGrade.value
  if (!g || g === '正常') return []
  return list.filter((x) => x.grade === g && x.value != null)
})

const indicatorGroups = computed(() => {
  const list = detail.value?.indicators || []
  return BASIS_ORDER.map((basis) => ({
    basis,
    ...BASIS_META[basis],
    rows: list.filter((x) => x.basis === basis).map((row) => ({
      ...row,
      meta: CARD_META[`${row.basis}|${row.gas}`] || {},
    })),
  })).filter((g) => g.rows.length)
})

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
function disabledDate(d) {
  if (!dateRange.value) return true
  const iso = formatDate(d)
  return iso < dateRange.value[0] || iso > dateRange.value[1]
}
function stepDay(delta) {
  const i = idx.value + delta
  if (i < 0 || i >= series.value.length) return
  selectedDate.value = series.value[i].date
}
/** 日历色标：红告警 / 橙注意2 / 黄注意1 / 绿正常（与 --lv-normal 一致） */
function cellClassName(d) {
  const iso = formatDate(d)
  const hit = series.value.find((s) => s.date === iso)
  if (!hit) return ''
  if (hit.grade === '告警值') return 'det-alarm'
  if (hit.grade === '注意值2') return 'det-w2'
  if (hit.grade === '注意值1') return 'det-w1'
  if (hit.grade === '正常') return 'det-normal'
  return ''
}
function fmtVal(row) {
  if (row.value == null) return '—'
  return row.value
}
function driverLabel(row) {
  const gas = String(row.item || '').replace(/值$/, '')
  const short = { 绝对浓度: '浓度', 绝对增量: '增量', 相对增长速率: '周增率' }[row.basis] || row.basis
  return `${short}·${gas}`
}
function fmtRate(v) {
  return v == null ? '—' : `${v}%/月`
}

async function loadSeries() {
  loadError.value = ''
  try {
    const res = await http.get('/detect/series')
    series.value = res.series || []
    summary.value = res.summary || {}
    if (!series.value.length) {
      loadError.value = '暂无监测数据，请先导入油中溶解气体时序'
      return
    }
    const q = typeof route.query.date === 'string' ? route.query.date : ''
    const fallback = res.summary?.date_range?.[1] || series.value.at(-1)?.date
    selectedDate.value = (q && series.value.some((s) => s.date === q)) ? q : fallback
  } catch (e) {
    loadError.value = e?.message || '加载全年序列失败'
    series.value = []
    summary.value = {}
  }
}
async function loadDay(date) {
  if (!date) return
  const req = date
  dayLoading.value = true
  dayError.value = ''
  try {
    const data = await http.get(`/detect/day/${date}`)
    // 防竞态：后发请求若日期已变则丢弃
    if (selectedDate.value !== req) return
    detail.value = data
  } catch (e) {
    if (selectedDate.value !== req) return
    detail.value = null
    dayError.value = e?.message || '加载当日详情失败'
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
})
</script>

<template>
  <div v-loading="loading" class="detect">
    <div v-if="loadError" class="gp empty-card">
      <div class="gp-body empty-body">{{ loadError }}</div>
    </div>

    <template v-else>
      <div class="gp">
        <div class="gp-head">选择监测日</div>
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
            </div>
          </div>
        </div>
      </div>

      <div v-loading="dayLoading" class="body">
        <div v-if="dayError" class="gp empty-card">
          <div class="gp-body empty-body">{{ dayError }}</div>
        </div>

        <template v-else-if="detail">
          <!-- 左：当日档；右：月环比 / 「预」 / 紧急度 -->
          <section class="gp day-kpis" :class="gradeClass(dayGrade)">
            <div class="gp-body day-kpis-body">
              <div class="kpi-left">
                <div class="day-grade-k">
                  当日最高档
                  <StdCite ref-id="1498-表A3" label="表A.3" inline />
                </div>
                <div class="day-grade-v">
                  <span class="pill" :class="gradeClass(dayGrade)">
                    <i class="d" />{{ dayGrade }}
                  </span>
                  <span v-if="isPre" class="pill pre-pill" title="含量档为正常/注意值1，月环比已超注意值">涨势预警</span>
                </div>
                <div v-if="maxDrivers.length" class="drivers-list">
                  <span
                    v-for="(row, i) in maxDrivers"
                    :key="i"
                    class="driver-chip"
                    :class="gradeClass(row.grade)"
                  >{{ driverLabel(row) }}</span>
                </div>
                <div v-else class="day-grade-s">七项均在正常范围</div>
              </div>

              <div class="kpi-right">
                <div class="rate-item">
                  <div class="rate-k">
                    总烃月环比
                    <StdCite ref-id="722-9.3.2" label="§9.3.2" inline />
                  </div>
                  <div class="rate-v" :class="{ hot: rateRising }">{{ fmtRate(thcRel) }}</div>
                  <p class="rate-hint">{{ rateHint }}</p>
                </div>
                <div class="rate-item">
                  <div class="rate-k">
                    涨势预警
                    <StdCite ref-id="722-9.3.3" label="§9.3.3 a" inline />
                  </div>
                  <div class="rate-v" :class="{ 'pre-hot': isPre }">{{ isPre ? '已触发' : '未触发' }}</div>
                  <p class="rate-hint">{{ preHint }}</p>
                </div>
                <div class="rate-item">
                  <div class="rate-k">处置紧急度</div>
                  <div class="rate-v" :class="{ hot: urgency?.level === '高' }">
                    {{ urgencyLabel }}
                  </div>
                  <p class="rate-hint">{{ urgencyHint }}</p>
                </div>
              </div>
            </div>
          </section>

          <section
            v-for="group in indicatorGroups"
            :key="group.basis"
            class="gp"
          >
          <div class="gp-head">
            <span class="head-title">{{ group.title }}</span>
            <span v-if="group.formula === 'a1'" class="formula" aria-label="式 A.1">
              ΔC<sub>w</sub> = C<sub>i,2</sub> − C<sub>i,1</sub>
            </span>
            <span v-else-if="group.formula === 'a2'" class="formula formula-a2" aria-label="式 A.2">
              ΔC<sub>r</sub> =
              <span class="frac">
                <span class="num">C<sub>i,2</sub> − C<sub>i,1</sub></span>
                <span class="den">C<sub>i,1</sub></span>
              </span>
              × 100%
            </span>
            <span class="head-ref">{{ group.unit }}</span>
          </div>
          <div class="gp-body">
            <div class="ind-grid" :class="{ single: group.rows.length === 1 }">
              <article
                v-for="row in group.rows"
                :key="row.basis + row.gas"
                class="ind"
                :class="[gradeClass(row.grade), { driver: dayGrade !== '正常' && row.grade === dayGrade }]"
              >
                <div class="ind-top">
                  <div class="ind-title">
                    <span class="ind-name">{{ row.item }}</span>
                    <span v-if="row.meta.en" class="ind-en mono">{{ row.meta.en }}</span>
                  </div>
                  <span class="pill mini" :class="gradeClass(row.grade)">
                    <i class="d" />{{ row.grade }}
                  </span>
                </div>

                <div class="ind-val mono">
                  {{ fmtVal(row) }}
                  <span class="ind-unit">{{ row.unit }}</span>
                </div>

                <p v-if="row.note" class="ind-note">{{ row.note }}</p>
              </article>
            </div>
          </div>
          </section>
        </template>
      </div>
    </template>
  </div>
</template>

<style scoped>
.detect { display: flex; flex-direction: column; gap: 12px; min-height: 200px; }

.empty-card { border-style: dashed; }
.empty-body { padding: 28px; text-align: center; color: var(--fg-3); font-size: 13px; }

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

.body { display: flex; flex-direction: column; gap: 12px; min-height: 120px; }

.day-kpis { border-left: 3px solid var(--line); }
.day-kpis.normal { border-left-color: var(--lv-normal); }
.day-kpis.w1 { border-left-color: var(--lv-w1); }
.day-kpis.w2 { border-left-color: var(--lv-w2); }
.day-kpis.alarm { border-left-color: var(--lv-alarm); }
.day-kpis-body {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
  gap: 16px 24px; padding: 14px 16px;
}
.kpi-left {
  display: flex; flex-direction: column; gap: 6px;
  min-width: 160px;
}
.kpi-right {
  display: flex; flex-wrap: wrap; align-items: stretch;
  gap: 8px 4px; margin-left: auto;
}
.kpi-right .rate-item {
  min-width: 148px;
  max-width: 220px;
  padding: 6px 14px;
  border-left: 1px solid var(--line);
}
.kpi-right .rate-item:first-child { border-left: none; }
.rate-hint {
  margin: 6px 0 0;
  font-size: 11px;
  line-height: 1.45;
  color: var(--fg-4);
  font-weight: 500;
}
.day-grade-k {
  display: flex; align-items: center; gap: 6px;
  font-size: 11px; color: var(--fg-4); font-weight: 600;
}
.day-grade-v { display: flex; align-items: center; gap: 8px; }
.day-grade-v .pill { font-size: 14px; padding: 4px 12px; }
.pre-pill {
  font-size: 12px; font-weight: 700; padding: 3px 10px; border-radius: 999px;
}
.day-grade-s { font-size: 12px; color: var(--fg-4); }
.drivers-list { display: flex; flex-wrap: wrap; gap: 6px; }
.driver-chip {
  display: inline-block;
  padding: 2px 8px; border-radius: 4px;
  font-size: 11px; font-weight: 600;
  border: 1px solid var(--line);
  background: var(--bg-3);
  color: var(--fg-2);
}
.driver-chip.w1 { border-color: rgba(251,191,36,0.35); color: var(--lv-w1); }
.driver-chip.w2 { border-color: rgba(251,146,60,0.4); color: var(--lv-w2); }
.driver-chip.alarm { border-color: rgba(245,85,90,0.4); color: var(--lv-alarm); }

.rate-k {
  display: flex; align-items: center; gap: 4px;
  font-size: 11px; color: var(--fg-4); font-weight: 600;
}
.rate-v { font-size: 18px; font-weight: 800; color: var(--fg); margin-top: 4px; }
.rate-v.hot { color: var(--lv-w2); }
.rate-v.pre-hot { color: var(--lv-pre-2); }

.head-title { flex-shrink: 0; }
.formula {
  margin-left: 10px;
  font-family: 'JetBrains Mono', 'Times New Roman', serif;
  font-size: 13px;
  font-weight: 600;
  color: var(--fg);
  letter-spacing: 0.02em;
  white-space: nowrap;
}
.formula sub { font-size: 0.72em; }
.formula-a2 {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.frac {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  line-height: 1.15;
  vertical-align: middle;
}
.frac .num {
  padding: 0 4px 1px;
  border-bottom: 1px solid var(--fg-2);
}
.frac .den { padding: 1px 4px 0; }
.head-ref {
  margin-left: auto; font-size: 10px; color: var(--fg-4);
  font-family: 'JetBrains Mono', monospace;
  max-width: 40%;
  text-align: right;
  line-height: 1.4;
}
.ind-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.ind-grid.single { grid-template-columns: 1fr; max-width: 420px; }
@media (max-width: 900px) {
  .ind-grid { grid-template-columns: 1fr; }
  .head-ref { max-width: 100%; text-align: left; margin-left: 0; margin-top: 4px; }
  .formula { white-space: normal; }
}

.ind {
  padding: 12px 14px;
  border-radius: var(--r);
  background: var(--bg-3);
  border: 1px solid var(--line);
  border-left-width: 3px;
  display: flex; flex-direction: column; gap: 6px;
  min-height: 100%;
}
.ind.normal { border-left-color: var(--lv-normal); }
.ind.w1 { border-left-color: var(--lv-w1); }
.ind.w2 { border-left-color: var(--lv-w2); }
.ind.alarm { border-left-color: var(--lv-alarm); }
.ind.driver {
  box-shadow: inset 0 0 0 1px rgba(45, 212, 191, 0.28);
}

.ind-top {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 8px;
}
.ind-title { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.ind-name { font-size: 13px; font-weight: 650; color: var(--fg); }
.ind-en { font-size: 11px; color: var(--teal-2); font-weight: 600; }
.pill.mini { font-size: 10px; padding: 2px 8px; flex-shrink: 0; }

.ind-val {
  font-size: 22px; font-weight: 800; color: var(--fg);
  line-height: 1.2;
}
.ind.w1 .ind-val { color: var(--lv-w1); }
.ind.w2 .ind-val { color: var(--lv-w2); }
.ind.alarm .ind-val { color: var(--lv-alarm); }
.ind-unit {
  font-size: 11px; font-weight: 600; color: var(--fg-4);
  margin-left: 4px;
}

.ind-note {
  margin: 0;
  font-size: 11px; color: var(--fg-4); line-height: 1.5;
}

.toolbar :deep(.el-input__wrapper) {
  background: var(--bg-3) !important;
  box-shadow: 0 0 0 1px var(--line-2) inset !important;
}
.toolbar :deep(.el-input__inner) { color: var(--fg) !important; }
</style>
