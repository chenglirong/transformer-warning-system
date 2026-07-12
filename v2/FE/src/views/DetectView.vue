<script setup>
// 气体分级检测 —— 选单日；表A.3 七项各自报档（含正常）+ 当日最高档
import { ref, computed, watch, onMounted } from 'vue'
import http from '@/service/http'
import StdCite from '@/components/StdCite.vue'

const loading = ref(true)
const series = ref([])
const summary = ref({})
const selectedDate = ref('')
const detail = ref(null)
const dayLoading = ref(false)

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
const abnormalDates = computed(() =>
  series.value.filter((s) => s.grade !== '正常').map((s) => s.date),
)

const dayGrade = computed(() => detail.value?.grade || null)

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
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}
function disabledDate(d) {
  if (!dateRange.value) return true
  const iso = formatDate(d)
  return iso < dateRange.value[0] || iso > dateRange.value[1]
}
function cellClassName(d) {
  const iso = formatDate(d)
  const hit = series.value.find((s) => s.date === iso)
  if (!hit) return ''
  if (hit.grade === '告警值') return 'det-alarm'
  if (hit.grade === '注意值2') return 'det-w2'
  if (hit.grade === '注意值1') return 'det-w1'
  return ''
}
function stepDay(delta) {
  const i = idx.value + delta
  if (i < 0 || i >= series.value.length) return
  selectedDate.value = series.value[i].date
}
function jumpAbnormal(dir) {
  const list = abnormalDates.value
  if (!list.length) return
  const cur = selectedDate.value
  if (dir < 0) {
    selectedDate.value = [...list].reverse().find((d) => d < cur) || list[list.length - 1]
  } else {
    selectedDate.value = list.find((d) => d > cur) || list[0]
  }
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

async function loadSeries() {
  const res = await http.get('/detect/series')
  series.value = res.series
  summary.value = res.summary
  selectedDate.value = res.summary.date_range?.[1] || res.series.at(-1)?.date
}
async function loadDay(date) {
  if (!date) return
  dayLoading.value = true
  try {
    detail.value = await http.get(`/detect/day/${date}`)
  } finally {
    dayLoading.value = false
  }
}

watch(selectedDate, (d) => loadDay(d))
onMounted(async () => {
  try { await loadSeries() } finally { loading.value = false }
})
</script>

<template>
  <div v-loading="loading" class="detect">
    <div class="gp">
      <div class="gp-head">
        选择监测日
        <StdCite ref-id="1498-表A3" label="DL/T 1498.2-2025 表A.3 原图" />
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
            class="date-pick"
          />
          <button type="button" class="btn btn-ghost" :disabled="idx < 0 || idx >= series.length - 1" @click="stepDay(1)">后日 ›</button>
        </div>
        <div class="nav">
          <button type="button" class="btn btn-ghost" :disabled="!abnormalDates.length" @click="jumpAbnormal(-1)">‹ 上一异常日</button>
          <button type="button" class="btn btn-ghost" :disabled="!abnormalDates.length" @click="jumpAbnormal(1)">下一异常日 ›</button>
        </div>
        <div class="status">
          <span class="meta mono">{{ selectedDate }}</span>
          <span class="meta">七项各自报档 · 含正常</span>
        </div>
      </div>
    </div>

    <div v-loading="dayLoading" class="body">
      <template v-if="detail">
        <section class="gp day-grade" :class="gradeClass(dayGrade)">
          <div class="gp-body day-grade-body">
            <div class="day-grade-main">
              <div class="day-grade-k">当日最高档</div>
              <div class="day-grade-v">
                <span class="pill" :class="gradeClass(dayGrade)">
                  <i class="d" />{{ dayGrade }}
                </span>
              </div>
              <div class="day-grade-s">表 A.3 七项判据取最高 · 不合成综合分</div>
            </div>
            <div v-if="maxDrivers.length" class="day-grade-drivers">
              <div class="drivers-k">抬档依据</div>
              <div class="drivers-list">
                <span
                  v-for="(row, i) in maxDrivers"
                  :key="i"
                  class="driver-chip"
                  :class="gradeClass(row.grade)"
                >{{ driverLabel(row) }}</span>
              </div>
            </div>
            <div v-else class="day-grade-drivers muted">
              七项均在正常范围
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
  </div>
</template>

<style scoped>
.detect { display: flex; flex-direction: column; gap: 12px; min-height: 200px; }

.toolbar { display: flex; flex-wrap: wrap; gap: 14px 20px; align-items: center; }
.nav { display: flex; align-items: center; gap: 8px; }
.date-pick { width: 160px; }
.status { display: flex; align-items: center; gap: 10px; margin-left: auto; }
.meta { font-size: 12px; color: var(--fg-3); }
.mono { font-family: 'JetBrains Mono', monospace; }

.body { display: flex; flex-direction: column; gap: 12px; min-height: 120px; }

.day-grade { border-left: 3px solid var(--line); }
.day-grade.normal { border-left-color: var(--lv-normal); }
.day-grade.w1 { border-left-color: var(--lv-w1); }
.day-grade.w2 { border-left-color: var(--lv-w2); }
.day-grade.alarm { border-left-color: var(--lv-alarm); }
.day-grade-body {
  display: flex; flex-wrap: wrap; align-items: center; gap: 16px 28px;
  padding: 14px 16px;
}
.day-grade-main { display: flex; flex-direction: column; gap: 6px; min-width: 160px; }
.day-grade-k { font-size: 11px; color: var(--fg-4); font-weight: 600; }
.day-grade-v .pill { font-size: 14px; padding: 4px 12px; }
.day-grade-s { font-size: 11px; color: var(--fg-4); }
.day-grade-drivers { flex: 1; min-width: 200px; }
.day-grade-drivers.muted { font-size: 12px; color: var(--fg-4); }
.drivers-k { font-size: 11px; color: var(--fg-4); margin-bottom: 6px; }
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

<style>
.el-date-table td.det-alarm .el-date-table-cell__text {
  background: rgba(245, 85, 90, 0.28) !important;
  color: #fca5a5 !important;
  border-radius: 50%;
}
.el-date-table td.det-w2 .el-date-table-cell__text {
  background: rgba(251, 146, 60, 0.25) !important;
  color: #fdba74 !important;
  border-radius: 50%;
}
.el-date-table td.det-w1 .el-date-table-cell__text {
  box-shadow: inset 0 -2px 0 #fbbf24;
}
</style>
