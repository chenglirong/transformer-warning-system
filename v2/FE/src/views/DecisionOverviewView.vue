<script setup>
// 监测决策 —— 检测周期 4 档 · 二次采样 3 档 · 试验建议
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import http from '@/service/http'
import StdCite from '@/components/StdCite.vue'
import TablePager from '@/components/TablePager.vue'

const router = useRouter()
const loading = ref(true)
const summary = ref({})
const allRecords = ref([])
const periodKinds = ref({})
const resampleKinds = ref({})

const summaryTab = ref('period')
const periodFilter = ref('')
const resampleFilter = ref('')
const trialsFilter = ref('')
const searchText = ref('')
const page = ref(1)
const pageSize = ref(20)

const modalOpen = ref(false)
const modalRow = ref(null)

const PERIOD_META = {
  baseline: { short: '基线周期', hint: '≤12h · 档位正常/未预警' },
  fast: { short: '快速采样', hint: '下限 ≤2h · 涨势/速率超' },
  baseline_watch: { short: '基线加强监视', hint: '≤12h · 紧急度低' },
  approach_fast: { short: '逼近快速周期', hint: '建议逼近 ≤2h · 注2/告警' },
}

const RESAMPLE_META = {
  none: { short: '不需要', hint: '未达预警' },
  suggest: { short: '建议验证', hint: '涨势/速率超或判型低可信' },
  defer: { short: '暂不建议', hint: '注2/告警且判型可信' },
}

const PERIOD_ORDER = ['baseline', 'fast', 'baseline_watch', 'approach_fast']
const RESAMPLE_ORDER = ['none', 'suggest', 'defer']
const TRIALS_ORDER = ['yes', 'no']

const gradeClass = (g) => ({
  正常: 'normal', 注意值1: 'w1', 注意值2: 'w2', 告警值: 'alarm',
}[g] || 'normal')

/** 类型名已含代码时不再尾缀，避免「T3 T3」 */
function faultLabel(type, code) {
  if (!type) return ''
  if (!code) return type
  const t = String(type)
  if (t.includes(code) || t.endsWith(code)) return t
  return `${t} ${code}`
}

const urgClass = (lv) => ({ 高: 'high', 中: 'mid', 低: 'low' }[lv] || '')

function confClass(c) {
  return { 高: 'high', 中: 'mid', 低: 'low' }[c] || ''
}

function rateText(r) {
  if (r.thc_rel_rate == null) return null
  return `${r.thc_rel_rate}%/月`
}

function rateTone(r) {
  if (r.is_pre) return 'pre'
  if (r.urgency_rising) return 'hot'
  if (r.thc_rel_rate != null && r.thc_rel_rate >= 10) return 'warn'
  return ''
}

function faultText(r) {
  if (!r.diagnose_triggered || !r.fault_type) return ''
  return faultLabel(r.fault_type, r.fault_code)
}

const TRIALS_META = {
  yes: { short: '有建议', hint: '附录 D / 1685-B' },
  no: { short: '无', hint: '无需开展检查性试验' },
}

const SUMMARY_TABS = [
  { id: 'period', label: '检测周期' },
  { id: 'resample', label: '二次采样' },
  { id: 'trials', label: '其他检查性试验' },
]

const kpiCards = computed(() => {
  if (summaryTab.value === 'trials') {
    const total = summary.value.total_days ?? 0
    const yes = summary.value.trials_count ?? 0
    return TRIALS_ORDER.map((id) => ({
      id,
      short: TRIALS_META[id].short,
      hint: TRIALS_META[id].hint,
      full: TRIALS_META[id].short,
      count: id === 'yes' ? yes : total - yes,
    }))
  }
  const isPeriod = summaryTab.value === 'period'
  const order = isPeriod ? PERIOD_ORDER : RESAMPLE_ORDER
  const meta = isPeriod ? PERIOD_META : RESAMPLE_META
  const counts = isPeriod ? summary.value.period_counts : summary.value.resample_counts
  const labels = isPeriod ? periodKinds.value : resampleKinds.value
  return order.map((id) => ({
    id,
    short: meta[id]?.short || id,
    hint: meta[id]?.hint || '',
    full: labels[id] || '',
    count: counts?.[id] ?? 0,
  }))
})

const kpiGridClass = computed(() => {
  if (summaryTab.value === 'period') return 'kpis-4'
  if (summaryTab.value === 'resample') return 'kpis-3'
  return 'kpis-2'
})

const filteredRows = computed(() => {
  let rows = [...allRecords.value]
  const q = searchText.value.trim().toLowerCase()

  if (periodFilter.value) {
    rows = rows.filter((r) => r.period_kind === periodFilter.value)
  }
  if (resampleFilter.value) {
    rows = rows.filter((r) => r.resample_kind === resampleFilter.value)
  }
  if (trialsFilter.value === 'yes') {
    rows = rows.filter((r) => (r.other_tests?.length ?? 0) > 0)
  } else if (trialsFilter.value === 'no') {
    rows = rows.filter((r) => !(r.other_tests?.length ?? 0))
  }

  if (q) {
    rows = rows.filter((r) => {
      const ot = Array.isArray(r.other_tests) ? r.other_tests.join(' ') : ''
      return [
        r.date, r.grade, String(r.thc_rel_rate ?? ''), r.urgency_level || '',
        r.fault_type || '', r.fault_code || '', r.fusion_confidence || '',
        r.period, r.resample, ot, r.decision_log,
      ].join(' ').toLowerCase().includes(q)
    })
  }

  rows.sort((a, b) => b.day - a.day)
  return rows
})

const pageRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredRows.value.slice(start, start + pageSize.value)
})

watch([searchText, pageSize, periodFilter, resampleFilter, trialsFilter], () => { page.value = 1 })
watch(summaryTab, () => { page.value = 1 })

function switchTab(id) {
  summaryTab.value = id
}

function openSummary(row) {
  modalRow.value = row
  modalOpen.value = true
}

function closeSummary() {
  modalOpen.value = false
  modalRow.value = null
}

function jumpDate() {
  return modalRow.value?.date || ''
}

function goAgent(date) {
  closeSummary()
  router.push({ path: '/agent', query: { date } })
}

function goDetect(date) {
  closeSummary()
  router.push({ path: '/detect', query: { date } })
}

function goDiagnose(date) {
  closeSummary()
  router.push({ path: '/diagnose', query: { date } })
}

async function loadOverview() {
  loading.value = true
  try {
    const res = await http.get('/decision/overview')
    summary.value = res.summary || {}
    allRecords.value = res.records || []
    periodKinds.value = res.period_kinds || {}
    resampleKinds.value = res.resample_kinds || {}
  } finally {
    loading.value = false
  }
}

onMounted(loadOverview)
</script>

<template>
  <div v-loading="loading" class="decision-page page-list">
    <section class="summary-panel gp">
      <div class="summary-head">
        <nav class="summary-tabs" aria-label="监测决策分类">
          <button
            v-for="t in SUMMARY_TABS"
            :key="t.id"
            type="button"
            class="tab"
            :class="{ on: summaryTab === t.id }"
            @click="switchTab(t.id)"
          >
            {{ t.label }}
          </button>
        </nav>
        <span class="summary-meta muted">全年 {{ summary.total_days ?? 0 }} 天</span>
      </div>

      <div class="kpis" :class="kpiGridClass">
      <div
        v-for="card in kpiCards"
        :key="card.id"
        class="kpi"
        :title="card.full"
      >
        <div class="kpi-k">{{ card.short }}</div>
        <div class="kpi-v teal">{{ card.count }}</div>
        <div class="kpi-s">{{ card.hint }}</div>
      </div>
      </div>
    </section>

    <section class="gp list-panel">
      <div class="gp-head toolbar">
        <input
          v-model="searchText"
          type="search"
          class="search"
          placeholder="搜索日期 / 档位 / 月环比 / 故障类型"
        />
        <label class="bar-filter">
          检测周期
          <select v-model="periodFilter" :class="{ on: periodFilter }">
            <option value="">全部</option>
            <option v-for="id in PERIOD_ORDER" :key="id" :value="id">
              {{ PERIOD_META[id].short }}
            </option>
          </select>
        </label>
        <label class="bar-filter">
          二次采样
          <select v-model="resampleFilter" :class="{ on: resampleFilter }">
            <option value="">全部</option>
            <option v-for="id in RESAMPLE_ORDER" :key="id" :value="id">
              {{ RESAMPLE_META[id].short }}
            </option>
          </select>
        </label>
        <label class="bar-filter">
          检查性试验
          <select v-model="trialsFilter" :class="{ on: trialsFilter }">
            <option value="">全部</option>
            <option value="yes">{{ TRIALS_META.yes.short }}</option>
            <option value="no">{{ TRIALS_META.no.short }}</option>
          </select>
        </label>
        <span class="head-ref">
          <StdCite ref-id="722-附录D" label="722 附录D 表D.1" />
          <StdCite ref-id="1685-附录B" label="1685 附录B 表B.2/B.3" />
        </span>
      </div>

      <div class="table-wrap">
        <table class="dga-table dec-table">
          <thead>
            <tr class="group-row">
              <th rowspan="2" class="col-date">日期</th>
              <th colspan="4" class="group-h group-basis">分析依据</th>
              <th colspan="3" class="group-h group-decision">监测决策</th>
              <th rowspan="2" class="col-actions">操作</th>
            </tr>
            <tr class="col-row">
              <th
                class="col-grade group-edge-basis"
                title="表 A.3 综合最高档"
              >当日最高档</th>
              <th class="col-urg" title="注意值2+ 结合月环比判急不急">处置紧急度</th>
              <th class="col-rate" title="722 总烃相对产气速率(%/月)；超注意值触发涨势预警">总烃月环比</th>
              <th class="col-diag" title="注意值2+ 或产气速率超时才判断；附可信度（高/中/低）">故障类型</th>
              <th class="col-period group-edge-decision">检测周期</th>
              <th>二次采样</th>
              <th>其他检查性试验</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in pageRows" :key="r.date">
              <td class="num col-date">{{ r.date }}</td>
              <td class="col-grade">
                <span class="pill mini" :class="gradeClass(r.grade)">
                  <i class="d" />{{ r.grade }}
                </span>
              </td>
              <td class="col-urg">
                <span
                  v-if="r.urgency_level"
                  class="urg-tag"
                  :class="urgClass(r.urgency_level)"
                >{{ r.urgency_level }}</span>
                <span v-else class="muted">—</span>
              </td>
              <td class="num col-rate" :class="rateTone(r)">
                <div class="rate-cell">
                  <span v-if="rateText(r)">{{ rateText(r) }}</span>
                  <span v-else class="muted">—</span>
                  <span v-if="r.is_pre" class="pre-tag" title="档未到注意值2，月环比已超注意值">涨势预警</span>
                </div>
              </td>
              <td class="col-diag">
                <template v-if="faultText(r)">
                  <span class="fault-text">{{ faultText(r) }}</span>
                  <span
                    v-if="r.fusion_confidence"
                    class="conf-tag block"
                    :class="confClass(r.fusion_confidence)"
                  >可信度 {{ r.fusion_confidence }}</span>
                </template>
                <span v-else class="muted">—</span>
              </td>
              <td class="col-period" :class="{ hot: r.period_kind !== 'baseline' }">{{ r.period }}</td>
              <td class="col-resample" :class="{ hot: r.resample_kind === 'suggest' }">{{ r.resample }}</td>
              <td class="col-ot" :class="{ hot: r.other_tests?.length }">
                <ul v-if="r.other_tests?.length" class="ot-list">
                  <li v-for="(t, ti) in r.other_tests" :key="ti">{{ t }}</li>
                </ul>
                <span v-else class="muted">—</span>
              </td>
              <td class="col-actions">
                <button type="button" class="act-btn" @click="openSummary(r)">查看摘要</button>
              </td>
            </tr>
            <tr v-if="!pageRows.length">
              <td colspan="9" class="empty">无匹配记录</td>
            </tr>
          </tbody>
        </table>
      </div>

      <TablePager
        v-model:page="page"
        v-model:page-size="pageSize"
        :total="filteredRows.length"
      />
    </section>

    <div v-if="modalOpen" class="modal" @keydown.esc="closeSummary">
      <div class="modal-backdrop" @click="closeSummary" />
      <div class="modal-dialog" role="dialog" aria-modal="true">
        <div class="modal-head">
          <div>
            <h3>{{ modalRow?.date || '…' }} 监测决策摘要</h3>
          </div>
          <button type="button" class="modal-x" aria-label="关闭" @click="closeSummary">×</button>
        </div>
        <div v-if="modalRow" class="modal-body">
          <table class="sum-table">
            <tbody>
              <tr class="sum-group">
                <th colspan="2">分析依据</th>
              </tr>
              <tr>
                <th>当日最高档</th>
                <td>
                  <span class="pill mini" :class="gradeClass(modalRow.grade)">
                    <i class="d" />{{ modalRow.grade }}
                  </span>
                  <span
                    v-if="modalRow.urgency_level"
                    class="urg-tag"
                    :class="urgClass(modalRow.urgency_level)"
                  >紧急度 {{ modalRow.urgency_level }}</span>
                </td>
              </tr>
              <tr>
                <th>总烃月环比</th>
                <td>
                  <span class="mono" :class="rateTone(modalRow)">{{ rateText(modalRow) || '—' }}</span>
                  <span v-if="modalRow.is_pre" class="pre-tag">涨势预警</span>
                </td>
              </tr>
              <tr>
                <th>故障类型</th>
                <td>
                  <template v-if="faultText(modalRow)">
                    {{ faultText(modalRow) }}
                    <span
                      v-if="modalRow.fusion_confidence"
                      class="conf-tag"
                      :class="confClass(modalRow.fusion_confidence)"
                    >可信度 {{ modalRow.fusion_confidence }}</span>
                  </template>
                  <span v-else class="muted">未触发判型</span>
                </td>
              </tr>
              <tr class="sum-group">
                <th colspan="2">监测决策</th>
              </tr>
              <tr>
                <th>检测周期</th>
                <td :class="{ hot: modalRow.period_kind !== 'baseline' }">{{ modalRow.period }}</td>
              </tr>
              <tr>
                <th>二次采样</th>
                <td :class="{ hot: modalRow.resample_kind === 'suggest' }">{{ modalRow.resample }}</td>
              </tr>
              <tr>
                <th>检查性试验</th>
                <td>
                  <ul v-if="modalRow.other_tests?.length" class="ot-list">
                    <li v-for="(t, ti) in modalRow.other_tests" :key="ti">{{ t }}</li>
                  </ul>
                  <span v-else class="muted">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="modal-foot">
          <button type="button" class="btn btn-ghost" @click="goDetect(jumpDate())">分级检测</button>
          <button
            type="button"
            class="btn btn-ghost"
            :disabled="!modalRow?.diagnose_triggered"
            @click="goDiagnose(jumpDate())"
          >故障判型</button>
          <button type="button" class="btn btn-primary" @click="goAgent(jumpDate())">Agent 分析</button>
          <button type="button" class="btn btn-ghost" @click="closeSummary">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>

.summary-panel .gp-body, .summary-panel { padding: 0; }
.summary-head {
  display: flex; flex-wrap: wrap; align-items: center; gap: 10px 16px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--line);
}
.summary-tabs { display: flex; flex-wrap: wrap; gap: 6px; }
.tab {
  border: 1px solid var(--line); background: var(--bg-3); color: var(--fg-3);
  border-radius: 6px; padding: 6px 14px; font-size: 12px; cursor: pointer;
}
.tab.on {
  border-color: rgba(45,212,191,0.45);
  color: var(--teal-2);
  background: rgba(45,212,191,0.1);
  font-weight: 600;
}
.summary-meta { font-size: 11px; margin-left: auto; }

.kpis { display: grid; gap: 10px; padding: 12px; }
.kpis-4 { grid-template-columns: repeat(4, 1fr); }
.kpis-3 { grid-template-columns: repeat(3, 1fr); }
.kpis-2 { grid-template-columns: repeat(2, 1fr); max-width: 520px; }
@media (max-width: 1100px) {
  .kpis-4 { grid-template-columns: repeat(2, 1fr); }
  .kpis-2 { max-width: none; }
}
@media (max-width: 700px) {
  .kpis-4, .kpis-3, .kpis-2 { grid-template-columns: 1fr; }
}

.kpi {
  padding: 12px 14px;
  border-radius: var(--r);
  background: var(--bg-2);
  border: 1px solid var(--line);
  text-align: left;
}
.kpi-k { font-size: 11px; color: var(--fg-3); }
.kpi-v {
  font-size: 26px; font-weight: 800; color: var(--fg); margin: 2px 0;
  font-family: 'JetBrains Mono', monospace;
}
.kpi-v.teal { color: var(--teal-2); }
.kpi-s { font-size: 11px; color: var(--fg-4); line-height: 1.4; }

.toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 12px; }
.search {
  flex: 1; min-width: 180px; max-width: 280px;
  padding: 5px 10px; border-radius: 6px;
  border: 1px solid var(--line-2); background: var(--bg-2); color: var(--fg); font-size: 12px;
}
.bar-filter {
  display: flex; align-items: center; gap: 6px;
  font-size: 11px; color: var(--fg-3); white-space: nowrap;
}
.bar-filter select {
  padding: 4px 8px; border-radius: 6px;
  border: 1px solid var(--line-2);
  background: var(--bg-2); color: var(--fg-3);
  font-size: 11px; cursor: pointer;
}
.bar-filter select.on {
  border-color: rgba(45,212,191,0.45);
  color: var(--teal-2);
  background: rgba(45,212,191,0.08);
}
.head-ref { font-size: 10.5px; color: var(--fg-4); display: flex; align-items: center; gap: 8px; margin-left: auto; }

.table-wrap { overflow-x: auto; }
.dec-table td { vertical-align: top; }
.dec-table td.col-grade { border-left: 2px solid rgba(147, 197, 253, 0.12); }
.dec-table td.col-period { border-left: 2px solid rgba(45, 212, 191, 0.15); }

.col-date { width: 108px; white-space: nowrap; }
.col-grade { width: 96px; white-space: nowrap; }
.col-urg { width: 72px; text-align: center; white-space: nowrap; }
.col-rate { width: 120px; white-space: nowrap; }
.rate-cell {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}
.col-rate .pre-tag {
  display: inline-flex;
  align-items: center;
  margin: 0;
  padding: 1px 7px;
  border-radius: 4px;
  border: 1px solid rgba(167, 139, 250, 0.45);
  background: rgba(167, 139, 250, 0.12);
  font-size: 10px;
  font-weight: 700;
  line-height: 1.4;
  color: var(--lv-pre-2, #c4b5fd);
}
.col-rate.pre { color: var(--lv-pre-2, #c4b5fd); }
.col-rate.hot { color: #fb923c; }
.col-rate.warn { color: #fbbf24; }
.col-diag { min-width: 130px; max-width: 200px; line-height: 1.45; font-size: 11.5px; }
.fault-text { display: block; }
.conf-tag,
.urg-tag {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  line-height: 1.4;
}
.conf-tag.block { display: block; width: fit-content; margin-top: 4px; }
.conf-tag.high { background: var(--lv-normal-bg); color: var(--lv-normal); }
.conf-tag.mid { background: var(--lv-w1-bg); color: var(--lv-w1); }
.conf-tag.low { background: var(--lv-alarm-bg); color: var(--lv-alarm); }
.urg-tag.high { background: rgba(245,85,90,0.15); color: var(--lv-alarm); }
.urg-tag.mid { background: rgba(251,146,60,0.15); color: var(--lv-w2); }
.urg-tag.low { background: rgba(45,212,191,0.12); color: var(--teal-2); }
.col-period, .col-resample, .col-ot { line-height: 1.45; font-size: 11.5px; }
.col-ot { max-width: 320px; vertical-align: top; }
.col-ot.hot { color: #93c5fd; }
.ot-list { margin: 0; padding-left: 16px; line-height: 1.5; }
.ot-list li { margin: 2px 0; }
.col-period.hot, .col-resample.hot { color: #93c5fd; }
.num { font-family: 'JetBrains Mono', monospace; font-size: 11px; }
.muted { color: var(--fg-4); font-size: 12px; }
.empty { text-align: center; color: var(--fg-4); padding: 24px; }

.modal {
  position: fixed; inset: 0; z-index: 80;
  display: flex; align-items: center; justify-content: center;
}
.modal-backdrop {
  position: absolute; inset: 0;
  background: rgba(0, 0, 0, 0.55);
}
.modal-dialog {
  position: relative;
  width: min(640px, calc(100vw - 32px));
  max-height: calc(100vh - 48px);
  overflow: hidden;
  display: flex; flex-direction: column;
  border-radius: var(--r-lg);
  border: 1px solid var(--line);
  background: var(--bg-2);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.45);
}
.modal-head {
  display: flex; justify-content: space-between; gap: 12px;
  padding: 14px 16px; border-bottom: 1px solid var(--line);
}
.modal-head h3 { margin: 0 0 4px; font-size: 15px; }
.modal-meta { font-size: 11px; color: var(--fg-4); }
.modal-x {
  border: none; background: transparent; color: var(--fg-3);
  font-size: 22px; cursor: pointer; line-height: 1;
}
.modal-body { padding: 14px 16px; overflow-y: auto; }
.sum-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
}
.sum-table th,
.sum-table td {
  padding: 9px 12px;
  border-bottom: 1px solid var(--line);
  vertical-align: top;
  text-align: left;
}
.sum-table tr:last-child th,
.sum-table tr:last-child td { border-bottom: none; }
.sum-table tr:not(.sum-group) th {
  width: 108px;
  font-weight: 500;
  color: var(--fg-4);
  background: var(--bg-3);
}
.sum-table tr:not(.sum-group) td {
  color: var(--fg-2);
  line-height: 1.45;
}
.sum-table td .pre-tag,
.sum-table td .urg-tag {
  margin-left: 6px;
}
.sum-table tr.sum-group th {
  padding: 7px 12px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--teal-2);
  background: rgba(45, 212, 191, 0.1);
  border-bottom: 1px solid var(--line);
}
.sum-table tr.sum-group:first-child th {
  color: #93c5fd;
  background: rgba(147, 197, 253, 0.1);
}
.sum-table .hot { color: #93c5fd; }
.sum-table .pre { color: var(--lv-pre-2, #c4b5fd); }
.sum-table .warn { color: #fbbf24; }
.sum-table .ot-list {
  margin: 0; padding-left: 16px; line-height: 1.5;
}
.sum-table .ot-list li { margin: 2px 0; }
.sum-table .conf-tag {
  margin-left: 6px;
}
.modal-foot {
  display: flex; justify-content: flex-end; flex-wrap: wrap; gap: 8px;
  padding: 12px 16px; border-top: 1px solid var(--line);
}
.mono { font-family: 'JetBrains Mono', monospace; }
</style>
