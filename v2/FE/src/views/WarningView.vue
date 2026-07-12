<script setup>
// 告警记录 —— 蓝图告警三层流水:
// ① 档位(表A.3) ② 超标判据 +「预」/处置紧急度 ③ 故障类型(注意值2+)
// 布局参考 alerts.html(KPI/筛选/分页),列按本系统字段自定
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import http from '@/service/http'
import StdCite from '@/components/StdCite.vue'

const router = useRouter()
const loading = ref(true)
const summary = ref({})
const allRecords = ref([])

const filter = ref('all')
const searchText = ref('')
const sortBy = ref('level-desc')
const page = ref(1)
const pageSize = ref(20)

const modalOpen = ref(false)
const modalLoading = ref(false)
const modalDetail = ref(null)

const FILTERS = [
  { id: 'all', label: '全部' },
  { id: 'abnormal', label: '仅异常' },
  { id: 'pre', label: '仅「预」' },
  { id: '注意值2', label: '注意值 2' },
  { id: '注意值1', label: '注意值 1' },
  { id: '告警值', label: '告警值' },
  { id: '正常', label: '正常' },
]

const GRADE_RANK = { 正常: 0, 注意值1: 1, 注意值2: 2, 告警值: 3 }

const gradeClass = (g) => ({
  正常: 'normal', 注意值1: 'w1', 注意值2: 'w2', 告警值: 'alarm',
}[g] || 'normal')

const urgClass = (lv) => ({ 高: 'high', 中: 'mid', 低: 'low' }[lv] || '')

const counts = computed(() => summary.value.grade_counts || {})

const filteredRows = computed(() => {
  let rows = [...allRecords.value]
  const f = filter.value
  const q = searchText.value.trim().toLowerCase()

  if (f === 'abnormal') {
    rows = rows.filter((r) => r.grade !== '正常' || r.is_pre)
  } else if (f === 'pre') {
    rows = rows.filter((r) => r.is_pre)
  } else if (f !== 'all') {
    rows = rows.filter((r) => r.grade === f)
  }

  if (q) {
    rows = rows.filter((r) => {
      const blob = [
        r.date, r.hits_text, r.grade, String(r.day),
        r.fault_type || '', r.fault_code || '',
        r.urgency_level || '',
      ].join(' ').toLowerCase()
      return blob.includes(q)
    })
  }

  rows.sort((a, b) => {
    if (sortBy.value === 'date-asc') return a.day - b.day
    if (sortBy.value === 'level-desc') {
      const d = (GRADE_RANK[b.grade] ?? 0) - (GRADE_RANK[a.grade] ?? 0)
      return d !== 0 ? d : b.day - a.day
    }
    return b.day - a.day
  })
  return rows
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredRows.value.length / pageSize.value)))

const pageRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredRows.value.slice(start, start + pageSize.value)
})

const rangeText = computed(() => {
  const n = filteredRows.value.length
  if (!n) return '无匹配记录'
  const start = (page.value - 1) * pageSize.value + 1
  const end = Math.min(page.value * pageSize.value, n)
  return `第 ${start}–${end} 条 · 第 ${page.value} / ${totalPages.value} 页`
})

const pageNums = computed(() => {
  const max = totalPages.value
  const cur = page.value
  if (max <= 7) return Array.from({ length: max }, (_, i) => i + 1)
  const pages = [1]
  const start = Math.max(2, cur - 1)
  const end = Math.min(max - 1, cur + 1)
  if (start > 2) pages.push('…')
  for (let p = start; p <= end; p++) pages.push(p)
  if (end < max - 1) pages.push('…')
  pages.push(max)
  return pages
})

watch([filter, searchText, sortBy, pageSize], () => { page.value = 1 })
watch(filteredRows, () => {
  if (page.value > totalPages.value) page.value = totalPages.value
})

// 表A.3 三组判据短名 —— 芯片必须带组别,否则「总烃」会重复三次分不清
const BASIS_SHORT = {
  绝对浓度: '浓度',
  绝对增量: '增量',
  相对增长速率: '周增率',
}

function hitLabel(h) {
  const basis = BASIS_SHORT[h.basis] || h.basis
  const gas = String(h.item || '').replace(/值$/, '')
  return `${basis}·${gas}→${h.grade}`
}

function rateText(r) {
  if (r.thc_rel_rate == null) return null
  return `${r.thc_rel_rate}%/月`
}

function rateTone(r) {
  // 连续超 10%/月 才驱动「预」/紧急度;列表用 rising 或 is_pre 标色
  if (r.is_pre || r.urgency_rising) return 'hot'
  if (r.thc_rel_rate != null && r.thc_rel_rate >= 10) return 'warn'
  return ''
}

function urgencyLabel(r) {
  return r.urgency_level || null
}

async function loadRecords() {
  loading.value = true
  try {
    const res = await http.get('/warning/records')
    allRecords.value = res.records || []
    summary.value = res.summary || {}
  } finally {
    loading.value = false
  }
}

async function openReport(row) {
  modalOpen.value = true
  modalLoading.value = true
  modalDetail.value = null
  try {
    modalDetail.value = await http.get(`/warning/day/${row.date}`)
  } finally {
    modalLoading.value = false
  }
}
function closeReport() {
  modalOpen.value = false
  modalDetail.value = null
}
function goDiagnose() {
  closeReport()
  router.push({ path: '/diagnose' })
}
function goDetect() {
  closeReport()
  router.push({ path: '/detect' })
}

onMounted(loadRecords)
</script>

<template>
  <div v-loading="loading" class="alerts">
    <div class="kpis">
      <div class="kpi">
        <div class="kpi-k">流水条数</div>
        <div class="kpi-v">{{ summary.total_days ?? 0 }}</div>
        <div class="kpi-s">四档全报 · 含正常</div>
      </div>
      <div class="kpi">
        <div class="kpi-k">注意值 1</div>
        <div class="kpi-v w1">{{ counts['注意值1'] ?? 0 }}</div>
        <div class="kpi-s">天</div>
      </div>
      <div class="kpi">
        <div class="kpi-k">注意值 2</div>
        <div class="kpi-v w2">{{ counts['注意值2'] ?? 0 }}</div>
        <div class="kpi-s">天 · 起判型 / 处置研判</div>
      </div>
      <div class="kpi">
        <div class="kpi-k">告警值</div>
        <div class="kpi-v alarm">{{ counts['告警值'] ?? 0 }}</div>
        <div class="kpi-s">「预」{{ summary.pre_count ?? 0 }} 次（档未超注意值2、速率已超）</div>
      </div>
    </div>

    <section class="gp">
      <div class="gp-head toolbar">
        <div class="toolbar-left">
          <div class="chips">
            <button
              v-for="f in FILTERS"
              :key="f.id"
              type="button"
              class="chip"
              :class="{ on: filter === f.id }"
              @click="filter = f.id"
            >
              {{ f.label }}
            </button>
          </div>
          <input
            v-model="searchText"
            type="search"
            class="search"
            placeholder="搜索日期 / 超标判据 / 故障类型"
          />
          <label class="sort">
            排序
            <select v-model="sortBy">
              <option value="date-desc">日期 ↓ 新→旧</option>
              <option value="date-asc">日期 ↑ 旧→新</option>
              <option value="level-desc">档位 ↓ 高→低</option>
            </select>
          </label>
        </div>
        <span class="head-ref">
          共 {{ filteredRows.length }} 条
          <template v-if="searchText.trim()"> · 已筛选</template>
          <StdCite ref-id="1498-表A3" label="表A.3" />
        </span>
      </div>

      <div class="table-wrap">
        <table class="alert-table">
          <thead>
            <tr>
              <th class="col-idx">#</th>
              <th class="col-date">日期</th>
              <th class="col-level">当日最高档</th>
              <th class="col-hits">超标判据（表A.3）</th>
              <th class="col-rate" title="DL/T 722 §9.3.2 总烃相对产气速率；与表A.3 周增率不是同一套">总烃月环比</th>
              <th class="col-pre" title="档位正常/注意值1 且月环比连续超 10%/月">「预」</th>
              <th class="col-urg" title="注意值2+ 结合月环比判急不急">处置紧急度</th>
              <th class="col-diag">故障类型</th>
              <th class="col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="r in pageRows"
              :key="r.date"
              :class="'lv-' + gradeClass(r.grade)"
            >
              <td class="num muted">{{ r.day }}</td>
              <td class="num">{{ r.date }}</td>
              <td>
                <span class="pill mini" :class="gradeClass(r.grade)">
                  <i class="d" />{{ r.grade }}
                </span>
              </td>
              <td class="col-hits">
                <template v-if="r.hits?.length">
                  <span
                    v-for="(h, i) in r.hits"
                    :key="i"
                    class="hit-chip"
                    :class="gradeClass(h.grade)"
                    :title="`${h.basis} · ${h.item} ${h.value ?? '—'} ${h.unit || ''}`"
                  >{{ hitLabel(h) }}</span>
                </template>
                <span v-else class="muted">—</span>
              </td>
              <td class="num col-rate" :class="rateTone(r)">
                <template v-if="rateText(r)">{{ rateText(r) }}</template>
                <span v-else class="muted">—</span>
              </td>
              <td class="col-pre">
                <span
                  v-if="r.is_pre"
                  class="pre-tag"
                  title="档未到注意值2，月环比已连续超阈 → 缩短检测周期"
                >预</span>
                <span v-else class="muted">—</span>
              </td>
              <td class="col-urg">
                <span v-if="urgencyLabel(r)" class="urg-tag" :class="urgClass(urgencyLabel(r))">
                  {{ urgencyLabel(r) }}
                </span>
                <span v-else class="muted">—</span>
              </td>
              <td class="col-diag">
                <template v-if="r.fault_type">
                  {{ r.fault_type }}
                  <span v-if="r.fault_code" class="code">{{ r.fault_code }}</span>
                </template>
                <span v-else class="muted">—</span>
              </td>
              <td class="col-actions">
                <button type="button" class="act-btn" @click="openReport(r)">查看摘要</button>
              </td>
            </tr>
            <tr v-if="!pageRows.length">
              <td colspan="9" class="empty">无匹配记录</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="foot">
        <div class="foot-meta">
          <label class="page-size">
            每页
            <select v-model.number="pageSize">
              <option :value="20">20</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
            </select>
            条
          </label>
          <span class="muted">{{ rangeText }}</span>
        </div>
        <div class="pager">
          <button type="button" class="page-btn" :disabled="page <= 1" @click="page--">上一页</button>
          <template v-for="(n, i) in pageNums" :key="i">
            <span v-if="n === '…'" class="ellipsis">…</span>
            <button
              v-else
              type="button"
              class="page-btn"
              :class="{ on: n === page }"
              @click="page = n"
            >
              {{ n }}
            </button>
          </template>
          <button type="button" class="page-btn" :disabled="page >= totalPages" @click="page++">下一页</button>
        </div>
      </div>
    </section>

    <div v-if="modalOpen" class="modal" @keydown.esc="closeReport">
      <div class="modal-backdrop" @click="closeReport" />
      <div class="modal-dialog" role="dialog" aria-modal="true">
        <div class="modal-head">
          <div>
            <h3>当日告警摘要</h3>
            <div class="modal-meta mono">
              {{ modalDetail?.date || '…' }}
              <template v-if="modalDetail"> · {{ modalDetail.grade }}</template>
              · Agent 表 G.1 完整报告待搭
            </div>
          </div>
          <button type="button" class="modal-x" aria-label="关闭" @click="closeReport">×</button>
        </div>
        <div v-loading="modalLoading" class="modal-body">
          <template v-if="modalDetail">
            <p class="sum">{{ modalDetail.hits_text }}</p>
            <div v-if="modalDetail.is_pre" class="pre-line">「预」：浓度未达注意值2，总烃相对速率连续超 10%/月</div>
            <div v-if="modalDetail.fault_type" class="fault">
              故障类型：{{ modalDetail.fault_type }}
              <span v-if="modalDetail.fault_code" class="code">{{ modalDetail.fault_code }}</span>
            </div>
            <div v-if="modalDetail.urgency" class="urg">
              处置研判（{{ modalDetail.urgency.level }}）：{{ modalDetail.urgency.advice }}
            </div>
            <div v-if="modalDetail.thc_rel_rate != null" class="rate-line">
              总烃相对产气速率（§9.3.2）：{{ modalDetail.thc_rel_rate }}%/月
            </div>
            <div class="ind-list">
              <div
                v-for="ind in modalDetail.indicators"
                :key="ind.basis + ind.item"
                class="ind-line"
                :class="gradeClass(ind.grade)"
              >
                <span>{{ ind.basis }} · {{ ind.item }}</span>
                <span class="mono">{{ ind.value == null ? '—' : ind.value }} {{ ind.unit }}</span>
                <span class="pill mini" :class="gradeClass(ind.grade)"><i class="d" />{{ ind.grade }}</span>
              </div>
            </div>
          </template>
        </div>
        <div class="modal-foot">
          <button type="button" class="btn btn-ghost" @click="goDetect">分级检测</button>
          <button type="button" class="btn btn-ghost" @click="goDiagnose">故障判型</button>
          <button type="button" class="btn btn-primary" @click="closeReport">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.alerts { display: flex; flex-direction: column; gap: 12px; }

.kpis {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
@media (max-width: 900px) {
  .kpis { grid-template-columns: repeat(2, 1fr); }
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
.kpi-v.w1 { color: var(--lv-w1); }
.kpi-v.w2 { color: var(--lv-w2); }
.kpi-v.alarm { color: var(--lv-alarm); }
.kpi-s { font-size: 11px; color: var(--fg-4); line-height: 1.4; }

.toolbar {
  flex-wrap: wrap;
  gap: 10px 12px;
  align-items: center;
}
.toolbar-left {
  display: flex; flex-wrap: wrap; align-items: center; gap: 10px 12px;
  flex: 1; min-width: 0;
}
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip {
  border: 1px solid var(--line);
  background: var(--bg-3);
  color: var(--fg-3);
  font-size: 11px; font-weight: 600;
  padding: 4px 10px; border-radius: 999px;
  cursor: pointer;
}
.chip.on {
  border-color: rgba(45,212,191,0.45);
  color: var(--teal-2);
  background: rgba(45,212,191,0.1);
}
.search {
  width: 220px; max-width: 100%;
  padding: 6px 12px; border-radius: 8px;
  border: 1px solid var(--line-2);
  background: var(--bg-3); color: var(--fg);
  font-size: 12px;
}
.search:focus { outline: none; border-color: rgba(45,212,191,0.45); }
.sort {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: var(--fg-3);
}
.sort select {
  padding: 5px 8px; border-radius: 6px;
  border: 1px solid var(--line-2);
  background: var(--bg-3); color: var(--fg);
  font-size: 12px; cursor: pointer;
}
.head-ref {
  margin-left: auto;
  display: inline-flex; align-items: center; gap: 8px;
  font-size: 11px; color: var(--fg-4);
}

.table-wrap {
  padding: 0;
  max-height: calc(100vh - 320px);
  overflow: auto;
}
.alert-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.alert-table thead th {
  position: sticky; top: 0; z-index: 2;
  text-align: left;
  padding: 10px 12px;
  font-size: 11px; font-weight: 600; color: var(--fg-4);
  background: var(--bg-2);
  border-bottom: 1px solid var(--line);
  white-space: nowrap;
}
.alert-table td {
  padding: 10px 12px;
  border-bottom: 1px solid rgba(160,174,192,0.1);
  color: var(--fg-2);
  vertical-align: middle;
}
.col-idx { width: 44px; }
.col-date { width: 100px; white-space: nowrap; }
.col-level { width: 96px; }
.col-hits { min-width: 240px; line-height: 1.55; }
.col-rate { width: 100px; text-align: right !important; white-space: nowrap; }
.col-pre { width: 52px; text-align: center; }
.col-urg { width: 72px; text-align: center; }
.col-diag { min-width: 140px; color: var(--fg-3); }
.col-actions { width: 96px; text-align: center; }
.num { font-family: 'JetBrains Mono', monospace; text-align: right; }
.num.warn { color: var(--lv-w1); }
.num.hot { color: #fbbf24; font-weight: 700; }
.muted { color: var(--fg-4); }
.pill.mini { font-size: 10px; padding: 2px 8px; }
.hit-chip {
  display: inline-block;
  margin: 0 4px 4px 0;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  background: var(--bg-3);
  border: 1px solid var(--line);
  color: var(--fg-2);
}
.hit-chip.w1 { border-color: rgba(251,191,36,0.35); color: var(--lv-w1); }
.hit-chip.w2 { border-color: rgba(251,146,60,0.4); color: var(--lv-w2); }
.hit-chip.alarm { border-color: rgba(245,85,90,0.4); color: var(--lv-alarm); }
.pre-tag {
  display: inline-block;
  padding: 1px 6px; border-radius: 4px;
  font-size: 10px; font-weight: 700;
  background: rgba(251,191,36,0.18); color: #fbbf24;
}
.urg-tag {
  display: inline-block;
  padding: 2px 8px; border-radius: 4px;
  font-size: 11px; font-weight: 700;
}
.urg-tag.high { background: rgba(245,85,90,0.15); color: var(--lv-alarm); }
.urg-tag.mid { background: rgba(251,146,60,0.15); color: var(--lv-w2); }
.urg-tag.low { background: rgba(45,212,191,0.12); color: var(--teal-2); }
.code {
  margin-left: 4px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px; color: var(--fg-4);
}
.alert-table tr.lv-w2 td { background: rgba(251,146,60,0.04); }
.alert-table tr.lv-alarm td { background: rgba(245,85,90,0.05); }
.empty { text-align: center; color: var(--fg-4); padding: 28px !important; }

.act-btn {
  height: 28px; padding: 0 10px; border-radius: 6px;
  border: 1px solid rgba(217,164,65,0.4);
  background: rgba(217,164,65,0.12);
  color: var(--amber-2);
  font-size: 11px; font-weight: 600; cursor: pointer;
}
.act-btn:hover { border-color: rgba(217,164,65,0.6); color: var(--fg); }

.foot {
  display: flex; align-items: center; justify-content: space-between;
  gap: 16px; flex-wrap: wrap;
  padding: 12px 14px;
  border-top: 1px solid var(--line);
  background: var(--bg-3);
}
.foot-meta { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.page-size {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: var(--fg-3);
}
.page-size select {
  padding: 4px 8px; border-radius: 6px;
  border: 1px solid var(--line-2);
  background: var(--bg-2); color: var(--fg);
  font-size: 12px;
}
.pager { display: flex; align-items: center; gap: 4px; }
.page-btn {
  min-width: 32px; height: 30px; padding: 0 8px;
  border-radius: 6px; border: 1px solid var(--line);
  background: var(--bg-2); color: var(--fg-2);
  font-size: 12px; cursor: pointer;
}
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.page-btn.on {
  border-color: rgba(45,212,191,0.45);
  color: var(--teal-2);
  background: rgba(45,212,191,0.1);
}
.ellipsis { color: var(--fg-4); padding: 0 4px; }

.modal {
  position: fixed; inset: 0; z-index: 80;
  display: flex; align-items: center; justify-content: center;
}
.modal-backdrop {
  position: absolute; inset: 0;
  background: rgba(0,0,0,0.55);
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
  box-shadow: 0 16px 48px rgba(0,0,0,0.45);
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
.sum { margin: 0 0 10px; font-size: 13px; color: var(--fg-2); line-height: 1.55; }
.pre-line { margin-bottom: 8px; font-size: 12px; color: #fbbf24; }
.fault { margin-bottom: 8px; font-size: 13px; color: var(--amber-2); font-weight: 650; }
.urg { margin-bottom: 8px; font-size: 12px; color: var(--fg-3); line-height: 1.55; }
.rate-line { margin-bottom: 12px; font-size: 12px; color: var(--fg-4); }
.ind-list { display: flex; flex-direction: column; gap: 6px; }
.ind-line {
  display: grid; grid-template-columns: 1.2fr 1fr auto; gap: 8px; align-items: center;
  padding: 8px 10px; border-radius: 6px; background: var(--bg-3);
  border-left: 3px solid var(--line); font-size: 12px;
}
.ind-line.normal { border-left-color: var(--lv-normal); }
.ind-line.w1 { border-left-color: var(--lv-w1); }
.ind-line.w2 { border-left-color: var(--lv-w2); }
.ind-line.alarm { border-left-color: var(--lv-alarm); }
.modal-foot {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 12px 16px; border-top: 1px solid var(--line);
}
.mono { font-family: 'JetBrains Mono', monospace; }
</style>
