<script setup>
// Agent 编排 —— 竖向七步流程 + 依据日志 + 表G.1 + 监测决策
// 判定全由国标规则;Agent B 优先 LLM 写人话,失败/无密钥降级规则模板
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import http from '@/service/http'
import StdCite from '@/components/StdCite.vue'
import ReportCardG from '@/components/ReportCardG.vue'
import AssistantPanel from '@/components/AssistantPanel.vue'

const route = useRoute()
const loading = ref(true)
const series = ref([])
const summary = ref({})
const selectedDate = ref('')

const running = ref(false)
const activeIdx = ref(-1)
const doneUpTo = ref(-1)
const result = ref(null)
const logs = ref([])
const reportReady = ref(false)
const modalOpen = ref(false)
const fullReportRef = ref(null)
const downloadBusy = ref(false)

const STEPS_META = [
  { icon: '1' },
  { icon: '2' },
  { icon: '3' },
  { icon: '4' },
  { icon: '5' },
  { icon: '6' },
  { icon: '7' },
]

const steps = computed(() => result.value?.steps || [])
const decision = computed(() => result.value?.decision || null)
const g1 = computed(() => result.value?.g1 || null)
const g2 = computed(() => result.value?.g2 || null)

/** 其他检查性试验：当前状态 / 依据 / 建议试验（卡片结构） */
function stripClauseFromName(test, clause) {
  if (!test) return ''
  let s = String(test)
  if (clause) s = s.replace(`(${clause})`, '')
  s = s.replace(/\(B\.[^)]+\)/g, '')
  return s.trim()
}

function clauseTableHint(clause) {
  const m = String(clause || '').match(/^(B\.\d+)/i)
  return m ? `表${m[1]}` : ''
}

const agentTrials = computed(() => {
  const blocks = g2.value?.other_tests_blocks
  if (Array.isArray(blocks) && blocks.length) {
    return {
      title: '其他检查性试验',
      blocks: blocks.map((b) => ({
        status: b.status,
        cite: b.cite,
        citeLabel: b.cite_label || b.cite,
        tableHint: b.table_hint || '',
        items: b.items || null,
        suggest: b.suggest || '',
        badge: b.badge || '',
      })),
      empty: false,
    }
  }
  const d = decision.value
  if (!d) return null
  const basisD = (d.trials_basis || []).find((b) => b.cite === '722-附录D' || b.label === '附录D')
  const nature = d.trials_nature_label || '—'
  const verify = d.trials_purpose === 'verify'
  const statusFromBasis = (basisD?.status || '').replace(/^当前状况：/, '').trim()
  const status = statusFromBasis
    || (verify ? `故障性质暂定为「${nature}」` : `故障性质为「${nature}」`)
  const dNames = d.trials_appendix_d?.length
    ? d.trials_appendix_d
    : (d.trials || []).filter((t) => !/\(B\./.test(t))
  const blocksFb = []
  if (dNames.length) {
    blocksFb.push({
      status,
      cite: '722-附录D',
      citeLabel: '722-附录D',
      tableHint: `表D.1「${nature}」列`,
      items: dNames,
      suggest: '',
      badge: '',
    })
  }
  for (const it of d.trials_1685_items || []) {
    blocksFb.push({
      status: it.why || '当日气体组合贴近附录B状态量描述',
      cite: '1685-附录B',
      citeLabel: '1685-附录B',
      tableHint: clauseTableHint(it.clause),
      items: null,
      suggest: stripClauseFromName(it.test, it.clause),
      badge: it.clause || '',
    })
  }
  return {
    title: '其他检查性试验',
    blocks: blocksFb,
    empty: !blocksFb.length,
  }
})

const reportMode = computed(() => result.value?.mode || 'rule_template')
const modeLabel = computed(() => (reportMode.value === 'llm' ? '大模型撰写' : '固定模板'))
const modeHint = computed(() => {
  if (reportMode.value === 'llm') return '分析意见由大模型撰写'
  const note = result.value?.opinion_note || result.value?.note
  return note || '规则模板成稿（未配置密钥或校验降级）'
})

const progressPct = computed(() => {
  if (!steps.value.length) return 0
  if (reportReady.value) return 100
  if (activeIdx.value < 0) return 0
  return Math.round(((activeIdx.value + 1) / steps.value.length) * 100)
})

const progressText = computed(() => {
  if (running.value && activeIdx.value >= 0 && steps.value[activeIdx.value]) {
    return `步骤 ${activeIdx.value + 1}/${steps.value.length} · ${steps.value[activeIdx.value].label}`
  }
  if (reportReady.value) return '流程完成 · 报告已生成'
  return '就绪'
})

const dateRange = computed(() => {
  if (!series.value.length) return null
  return [series.value[0].date, series.value[series.value.length - 1].date]
})

const idx = computed(() => series.value.findIndex((s) => s.date === selectedDate.value))

const gradeClass = (g) => ({
  正常: 'normal', 注意值1: 'w1', 注意值2: 'w2', 告警值: 'alarm',
}[g] || 'normal')

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
/** 日历色标：与分级页一致，仅四档（涨势预警不单独上色） */
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
function stepDay(delta) {
  if (running.value) return
  const i = idx.value + delta
  if (i < 0 || i >= series.value.length) return
  selectedDate.value = series.value[i].date
}
function stepState(i) {
  if (i < doneUpTo.value) return 'done'
  if (i === activeIdx.value) return 'active'
  return 'pending'
}

function pad(n) {
  return n < 10 ? `0${n}` : `${n}`
}
function nowTs() {
  const t = new Date()
  return `${pad(t.getHours())}:${pad(t.getMinutes())}:${pad(t.getSeconds())}`
}

/** 后端 log_lines → 前端展示行（补 ts，统一 camelCase） */
function normalizeLogLine(line) {
  return {
    id: line.id,
    tag: line.tag,
    severity: line.severity || 'muted',
    cite: line.cite ?? null,
    citeIds: line.cite_ids ?? line.citeIds ?? [],
    cat: line.cat,
    msg: line.msg,
    highlight: Boolean(line.highlight),
    conclusionTone: line.conclusion_tone ?? line.conclusionTone,
    showCite: line.show_cite ?? line.showCite ?? false,
    ts: nowTs(),
  }
}

/** 监测决策面板固定色 */
function decisionTone() {
  return 'agent'
}

async function loadSeries() {
  const res = await http.get('/detect/series')
  series.value = res.series || []
  summary.value = res.summary || {}
  const q = typeof route.query.date === 'string' ? route.query.date : ''
  const fallback = res.summary?.default_date || series.value.at(-1)?.date
  selectedDate.value = (q && series.value.some((s) => s.date === q)) ? q : fallback
}

function wantsOpenReport() {
  return route.query.report === '1' || route.query.report === 'true'
}

/** 带 ?date= 从别的页跳入 → 自动跑选中日；从左菜单进(无 date)则需手点 */
function wantsAutoRun() {
  return typeof route.query.date === 'string' && route.query.date !== ''
}

/** 告警弹窗跳入：切日 + 静默出结果并打开完整报告 */
async function applyReportDeepLink() {
  const q = typeof route.query.date === 'string' ? route.query.date : ''
  if (!wantsOpenReport() || !q || !series.value.some((s) => s.date === q)) return
  if (selectedDate.value !== q) selectedDate.value = q
  await runAgent({ animate: false, openReport: true })
}

function periodCiteLabel(id) {
  return ({
    '1498-A.3.1': 'A.3.1',
    '1498-A.3.2': 'A.3.2',
    '1498-A.3.3': 'A.3.3',
    '1498-5.5.5': '§5.5.5',
    '1498-5.4.5': '§5.4.5',
    '722-9.3.3': '§9.3.3',
    '722-5.4': '§5.4',
    '722-附录D': '附录D',
    '1685-附录B': '1685-B',
  })[id] || id || '—'
}

function resetUi() {
  activeIdx.value = -1
  doneUpTo.value = -1
  logs.value = []
  reportReady.value = false
  modalOpen.value = false
  result.value = null
}

/**
 * @param {{ animate?: boolean, openReport?: boolean }} opts
 * animate=false：跳过逐步播放，立刻铺满步骤/日志（告警深链用）
 */
async function runAgent(opts = {}) {
  const animate = opts.animate !== false
  const openAfter = Boolean(opts.openReport)
  if (running.value || !selectedDate.value) return
  running.value = true
  resetUi()
  try {
    const data = await http.get('/agent/run', {
      day: selectedDate.value,
    })
    await applyAgentPayload(data, { animate, openReport: openAfter })
  } catch (e) {
    result.value = null
    reportReady.value = false
    logs.value.push({
      ts: nowTs(),
      cat: '错误',
      tag: 'agent',
      severity: 'alarm',
      msg: e?.message || String(e),
      cite: null,
      citeIds: [],
      showCite: false,
    })
  } finally {
    running.value = false
  }
}

/** 将编排结果灌入主界面 */
async function applyAgentPayload(data, opts = {}) {
  const animate = opts.animate !== false
  const openAfter = Boolean(opts.openReport)
  if (!data) return
  if (data.date) selectedDate.value = data.date
  result.value = data
  if (animate) {
    await playSteps(data.steps || [], data.log_lines || [])
  } else {
    applyStepsInstant(data.log_lines || [])
  }
  reportReady.value = true
  if (openAfter) modalOpen.value = true
}

function applyStepsInstant(logLines) {
  logs.value = (logLines || []).map(normalizeLogLine)
  doneUpTo.value = (result.value?.steps || []).length
  activeIdx.value = -1
}

async function playSteps(steps, logLines) {
  const all = logLines || []
  for (let i = 0; i < steps.length; i++) {
    if (i > 0) doneUpTo.value = i
    activeIdx.value = i
    const stepId = steps[i].id
    const subLines = all.filter((l) => l.id === stepId).map(normalizeLogLine)
    for (let j = 0; j < subLines.length; j++) {
      logs.value.push({ ...subLines[j], ts: nowTs() })
      await nextTick()
      const el = document.getElementById('agent-log')
      if (el) el.scrollTop = el.scrollHeight
      const lastSub = j === subLines.length - 1
      const lastStep = i === steps.length - 1
      const delay = lastSub ? (lastStep ? 450 : 320) : 90
      await sleep(delay)
    }
  }
  doneUpTo.value = steps.length
  activeIdx.value = -1
}

/** 行级色调（后端 conclusion_tone / severity） */
function logRowTone(line) {
  return line?.conclusionTone || line?.severity || 'muted'
}

/** 流式日志 HTML：前缀置灰，结论加亮（v-html 内用 tone-*，配合 :deep） */
function formatLogHtml(line) {
  const raw = String(line?.msg || '')
  const esc = raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  const withUnit = (line?.id === 'input' || line?.cat === '气体')
    ? esc.replace(/µL\/L|μL\/L/g, '<span class="gas-unit">µL/L</span>')
    : esc
  const isGas = line?.id === 'input' || line?.cat === '气体'
  const toneCls = isGas ? '' : ` tone-${logRowTone(line)}`

  const arrowIdx = withUnit.indexOf('→')
  if (arrowIdx >= 0) {
    const head = withUnit.slice(0, arrowIdx)
    const tail = withUnit.slice(arrowIdx + 1).trim()
    return `<span class="msg-dim">${head}</span><span class="msg-arrow">→</span><span class="msg-result${toneCls}">${tail}</span>`
  }

  if (line?.highlight) {
    return `<span class="msg-result${toneCls}">${withUnit}</span>`
  }
  return withUnit
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms))
}

function openReport() {
  if (!reportReady.value) return
  modalOpen.value = true
}
function closeReport() {
  modalOpen.value = false
}

async function downloadReportPdf() {
  if (!g1.value || downloadBusy.value) return
  downloadBusy.value = true
  try {
    await fullReportRef.value?.downloadPdf()
  } catch (e) {
    window.alert(e?.message || 'PDF 导出失败，请重试')
  } finally {
    downloadBusy.value = false
  }
}

const bootReady = ref(false)
const assistantOpen = ref(false)

function toggleAssistant() {
  assistantOpen.value = !assistantOpen.value
}

/** 助手返回分析结果时同步刷新主区时间线/报告 */
async function onAssistantResult(r) {
  if (!r) return
  await applyAgentPayload(r, { animate: false })
}

function onAssistantDay(day) {
  if (day && day !== selectedDate.value) selectedDate.value = day
}

onMounted(async () => {
  try {
    await loadSeries()
  } finally {
    loading.value = false
  }
  bootReady.value = true
  if (route.query.assistant === '1') {
    assistantOpen.value = true
  }
  // 告警弹窗深链（?date=&report=1）静默出报告并打开完整报告
  if (wantsOpenReport()) {
    await applyReportDeepLink()
  } else if (wantsAutoRun()) {
    // 其它页带 ?date= 跳入：自动跑选中日（不打开报告弹窗）
    await runAgent()
  }
  // 从左菜单进页（无 date）：不自动跑，需手点
})

watch(
  () => [route.query.date, route.query.report],
  async () => {
    if (!bootReady.value || running.value) return
    if (wantsOpenReport()) await applyReportDeepLink()
  },
)

// 日期变更：不自动跑，且清空上一份结果，避免串日
watch(selectedDate, (d, prev) => {
  if (!bootReady.value || !d || d === prev || running.value) return
  if (wantsOpenReport()) return // 深链流程自己会跑
  resetUi()
})
</script>

<template>
  <div v-loading="loading" class="agent">
    <div class="gp toolbar-card">
      <div class="gp-body toolbar">
        <div class="nav">
          <button type="button" class="btn btn-ghost" :disabled="running || idx <= 0" @click="stepDay(-1)">‹ 前日</button>
          <el-date-picker
            v-model="selectedDate"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            :disabled-date="disabledDate"
            :cell-class-name="cellClassName"
            popper-class="dga-cal-popper"
            :disabled="running"
            class="date-pick"
          />
          <button
            type="button"
            class="btn btn-ghost"
            :disabled="running || idx < 0 || idx >= series.length - 1"
            @click="stepDay(1)"
          >后日 ›</button>
          <div class="cal-legend" aria-label="日历色标">
            <span><i class="lg alarm" />告警</span>
            <span><i class="lg w2" />注意2</span>
            <span><i class="lg w1" />注意1</span>
            <span><i class="lg normal" />正常</span>
          </div>
        </div>
        <div class="actions">
          <button type="button" class="btn btn-action" :disabled="!reportReady" @click="openReport">
            完整报告
          </button>
          <button type="button" class="btn btn-primary" :disabled="running || !selectedDate" @click="runAgent()">
            {{ running ? '运行中…' : reportReady ? '重新运行' : '运行分析' }}
          </button>
          <button
            type="button"
            class="btn-assistant"
            :class="{ active: assistantOpen }"
            @click="toggleAssistant"
          >
            分析助手
          </button>
        </div>
      </div>
    </div>

    <div class="agent-layout">
      <!-- 左：竖向七步 -->
      <section class="gp flow-panel">
        <div class="gp-head">
          分析流程
        </div>
        <div class="gp-body flow-body">
          <div class="v-pipeline">
            <div
              v-for="(s, i) in (steps.length ? steps : [
                { label: '当日气体', sub: '七气浓度' },
                { label: '分级检测', sub: '浓度 · 增量 · 增速综合分档' },
                { label: '产气趋势', sub: '总烃月环比与涨势判断' },
                { label: '处置紧急度', sub: '高 / 中 / 低紧急度' },
                { label: '故障判型', sub: '三法交叉研判' },
                { label: '监测决策', sub: '检测周期 · 二次采样 · 试验建议' },
                { label: '生成报告', sub: '档案卡片与分析意见' },
              ])"
              :key="i"
              class="v-step"
              :class="[stepState(i), { output: i === 6 }]"
            >
              <div class="v-track">
                <div class="v-node">{{ STEPS_META[i]?.icon || i + 1 }}</div>
                <div v-if="i < 6" class="v-line" :class="{ flowing: doneUpTo > i }" />
              </div>
              <div class="v-body">
                <div class="v-text">
                  <div class="label">{{ s.label }}</div>
                  <div class="sub">{{ s.sub }}</div>
                </div>
                <span class="v-badge">
                  {{ stepState(i) === 'done' ? '完成' : stepState(i) === 'active' ? '进行中' : '待执行' }}
                </span>
              </div>
            </div>
          </div>
          <div class="flow-progress">
            <div class="bar"><div class="fill" :style="{ width: progressPct + '%' }" /></div>
            <div class="meta">
              <span>{{ progressText }}</span>
              <span>7 步</span>
            </div>
          </div>
        </div>
      </section>

      <!-- 右：日志 + 输出 -->
      <div class="main-col">
        <section class="gp log-panel">
          <div class="gp-head">
            运行日志
            <span class="head-hint-flow">依据</span>
          </div>
          <div id="agent-log" class="gp-body log-body log-stream">
            <div v-if="!logs.length" class="log-empty">点击「运行分析」查看逐步结论</div>
            <div
              v-for="(line, i) in logs"
              :key="i"
              class="log-row"
              :class="[
                'sev-' + logRowTone(line),
                { 'log-gas': line.cat === '气体' },
              ]"
            >
              <span class="ts">{{ line.ts }}</span>
              <span class="cat">[{{ line.cat }}]</span>
              <span class="msg" v-html="formatLogHtml(line)" />
              <span v-if="line.showCite && line.citeIds?.length" class="log-cites">
                <StdCite
                  v-for="cid in line.citeIds"
                  :key="cid"
                  :ref-id="cid"
                  inline
                />
              </span>
            </div>
          </div>
        </section>

        <div class="output-row">
          <section class="gp g1-panel">
            <div class="gp-head">
              输出预览 · 分析报告
              <button type="button" class="btn btn-ghost mini" :disabled="!reportReady" @click="openReport">
                完整报告
              </button>
            </div>
            <div class="gp-body g1-body">
              <div class="g1-preview" :class="reportReady ? 'unlocked' : 'locked'">
                <ReportCardG
                  v-if="g1"
                  :g1="g1"
                  :g2="g2"
                  mode="compact"
                  :show-g2="true"
                  :show-cites="false"
                />
                <div v-else class="g1-placeholder">流程完成后解锁分析报告预览</div>
              </div>
            </div>
          </section>

          <section class="gp decision-panel">
            <div class="gp-head">
              监测决策
            </div>
            <div class="gp-body decision-body">
              <template v-if="reportReady && decision">
                <div class="dec-item">
                  <div class="dec-k">建议检测周期</div>
                  <div class="dec-v" :class="decisionTone()">{{ decision.period }}</div>
                  <div class="dec-s">
                    <span class="dec-basis-k">依据</span>
                    <StdCite
                      v-if="decision.cite_period"
                      inline
                      :ref-id="decision.cite_period"
                      :label="decision.cite_period"
                    />
                  </div>
                </div>
                <div class="dec-item">
                  <div class="dec-k">二次采样</div>
                  <div class="dec-v" :class="decisionTone()">{{ decision.resample }}</div>
                  <div class="dec-s">
                    <span class="dec-basis-k">依据</span>
                    <StdCite
                      v-if="decision.cite_resample"
                      inline
                      :ref-id="decision.cite_resample"
                      :label="decision.cite_resample"
                    />
                  </div>
                </div>
                <div class="dec-item trials-panel">
                  <div class="tp-top">
                    <div class="tp-title">{{ agentTrials?.title || '其他检查性试验' }}</div>
                  </div>

                  <template v-if="agentTrials && !agentTrials.empty">
                    <div
                      v-for="(ch, i) in agentTrials.blocks"
                      :key="'ot'+i"
                      class="tp-block"
                    >
                      <dl class="tp-chain">
                        <div class="tp-row">
                          <dt>当前状态</dt>
                          <dd>{{ ch.status }}</dd>
                        </div>
                        <div class="tp-row">
                          <dt>依据</dt>
                          <dd class="tp-basis">
                            <StdCite
                              v-if="ch.cite"
                              inline
                              :ref-id="ch.cite"
                              :label="ch.citeLabel"
                            />
                            <span v-if="ch.tableHint" class="tp-table-hint">{{ ch.tableHint }}</span>
                          </dd>
                        </div>
                        <div class="tp-row">
                          <dt>建议试验</dt>
                          <dd>
                            <ul v-if="ch.items?.length" class="tp-items">
                              <li v-for="(name, ni) in ch.items" :key="'oti'+ni">{{ name }}</li>
                            </ul>
                            <template v-else>
                              {{ ch.suggest || '—' }}
                            </template>
                          </dd>
                        </div>
                      </dl>
                    </div>
                  </template>
                  <div v-else class="dec-s">—</div>
                </div>
              </template>
              <div v-else class="decision-lock">等待流程完成</div>
            </div>
          </section>
        </div>
      </div>
    </div>

    <AssistantPanel
      :visible="assistantOpen"
      :selected-date="selectedDate"
      :agent-result="result"
      :disabled="running"
      @close="assistantOpen = false"
      @analysis-result="onAssistantResult"
      @selected-day="onAssistantDay"
    />

    <!-- 完整报告弹层：国标表 G.1 + 表 G.2 -->
    <div v-if="modalOpen && g1" class="modal">
      <div class="modal-backdrop" @click="closeReport" />
      <div class="modal-dialog" role="dialog">
        <div class="modal-head">
          <div>
            <h3>完整分析报告</h3>
            <div class="modal-meta">
              {{ g1.report_no }} · 分析报告 · {{ modeLabel }}
              <span v-if="result?.grade" class="modal-grade" :class="gradeClass(result.grade)">
                {{ result.grade }}
              </span>
            </div>
          </div>
          <button type="button" class="modal-x" @click="closeReport">×</button>
        </div>
        <div class="modal-body">
          <ReportCardG
            ref="fullReportRef"
            :g1="g1"
            :g2="g2"
            mode="full"
            :show-cites="false"
          />
        </div>
        <div class="modal-foot">
          <button type="button" class="btn btn-primary" :disabled="downloadBusy" @click="downloadReportPdf">
            {{ downloadBusy ? '导出中…' : '下载 PDF' }}
          </button>
          <button type="button" class="btn btn-ghost" @click="closeReport">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.agent { display: flex; flex-direction: column; gap: 12px; min-height: 0; }

.toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 12px 16px; }
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
.meta { font-size: 12px; color: var(--fg-3); }
.actions { display: flex; gap: 8px; margin-left: auto; align-items: center; }
.btn-assistant {
  background: rgba(139, 92, 246, 0.1);
  color: #a78bfa;
  border: 1px solid rgba(139, 92, 246, 0.35);
  border-radius: 6px;
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, box-shadow 0.15s;
}
.btn-assistant:hover { background: rgba(139, 92, 246, 0.18); box-shadow: 0 0 12px rgba(139, 92, 246, 0.2); }
.btn-assistant.active { background: rgba(139, 92, 246, 0.22); border-color: rgba(139, 92, 246, 0.6); }
.btn-action {
  background: rgba(45, 212, 191, 0.08);
  color: var(--teal-2);
  border-color: rgba(45, 212, 191, 0.45);
}
.btn-action:hover:not(:disabled) {
  background: rgba(45, 212, 191, 0.14);
  color: var(--teal-2);
  box-shadow: 0 0 12px rgba(45, 212, 191, 0.2);
}
.btn.mini { padding: 2px 8px; font-size: 10px; height: auto; }

.agent-layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 12px;
  min-height: 0;
  flex: 1;
}
@media (max-width: 1024px) {
  .agent-layout { grid-template-columns: 1fr; }
}

.flow-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: calc(100vh - 200px);
}
.flow-body {
  display: flex; flex-direction: column; gap: 12px;
  padding: 14px 12px !important;
  max-height: calc(100vh - 260px);
  overflow-y: auto;
}

.v-pipeline { display: flex; flex-direction: column; }
.v-step { display: flex; gap: 12px; }
.v-track {
  display: flex; flex-direction: column; align-items: center;
  width: 32px; flex-shrink: 0;
}
.v-node {
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  background: var(--bg-3); border: 2px solid var(--line);
  color: var(--fg-4); z-index: 1; transition: all 0.3s;
}
.v-line {
  flex: 1; width: 2px; min-height: 18px;
  background: rgba(160,174,192,0.15); margin: 4px 0;
  position: relative; overflow: hidden;
}
.v-line::after {
  content: ''; position: absolute; inset: 0 auto auto 0;
  width: 100%; height: 0;
  background: linear-gradient(180deg, var(--teal), #d4a017);
  transition: height 0.45s ease;
}
.v-line.flowing::after { height: 100%; }
.v-body {
  flex: 1; display: flex; gap: 8px; align-items: flex-start;
  padding: 2px 0 14px; min-width: 0;
}
.v-text { flex: 1; min-width: 0; }
.v-text .label { font-size: 13px; font-weight: 650; color: var(--fg-2); }
.v-text .sub { font-size: 10px; color: var(--fg-4); margin-top: 2px; line-height: 1.4; }
.step-cite { margin-top: 4px; display: inline-flex; }
.v-badge {
  font-size: 10px; font-weight: 600; color: var(--fg-4);
  padding: 2px 6px; border-radius: 4px; background: var(--bg-3);
  white-space: nowrap; margin-top: 4px;
}
.v-step.active .v-node {
  border-color: var(--teal); color: var(--teal-2);
  box-shadow: 0 0 0 3px rgba(45,212,191,0.15);
}
.v-step.active .v-badge { color: var(--teal-2); background: rgba(45,212,191,0.12); }
.v-step.active .label { color: var(--fg); }
.v-step.done .v-node {
  border-color: rgba(45,212,191,0.5); color: var(--teal-2);
  background: rgba(45,212,191,0.1);
}
.v-step.done .v-badge { color: var(--teal-2); }
.v-step.output.active .v-node,
.v-step.output.done .v-node { border-color: #d4a017; color: #f0c674; }

.mode-hint {
  font-size: 11px; color: var(--fg-4); max-width: 220px;
  line-height: 1.35; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.btn-link {
  border: none; background: transparent; padding: 0 2px;
  font-size: 11px; color: var(--fg-4); cursor: pointer;
  text-decoration: underline; text-underline-offset: 2px;
}
.btn-link:hover:not(:disabled) { color: var(--fg-3); }
.btn-link:disabled { opacity: 0.45; cursor: not-allowed; }

.flow-progress { margin-top: auto; padding-top: 8px; }
.bar { height: 4px; border-radius: 2px; background: var(--bg-3); overflow: hidden; }
.fill { height: 100%; background: linear-gradient(90deg, var(--teal), #d4a017); transition: width 0.35s; }
.meta {
  display: flex; justify-content: space-between;
  margin-top: 6px; font-size: 11px; color: var(--fg-4);
}

.main-col { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.log-panel { flex: 1; min-height: 180px; display: flex; flex-direction: column; }

.traj-block { padding-bottom: 10px; }
.traj-row {
  display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px;
  font-size: 11.5px; line-height: 1.45; padding: 4px 0;
  border-bottom: 1px dashed var(--line);
}
.traj-row:last-child { border-bottom: none; }
.traj-cond { color: var(--fg-4); }
.traj-arrow { color: var(--fg-4); }
.traj-act { color: var(--fg); font-weight: 650; }

.head-hint { margin-left: auto; font-size: 10px; color: var(--fg-4); font-weight: 500; }
.head-hint-flow {
  margin-left: auto; font-size: 10px; color: var(--fg-4);
  font-family: 'JetBrains Mono', monospace;
}
.traj-cite {
  font-size: 10px; color: var(--fg-4);
  font-family: 'JetBrains Mono', monospace;
}
.log-body {
  max-height: 360px;
  overflow-y: auto;
}
.log-stream {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 8px;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 10.5px;
  line-height: 1.45;
  background: var(--bg-2);
}
.log-empty {
  color: var(--fg-4);
  padding: 20px 0;
  text-align: center;
  font-family: system-ui, sans-serif;
}
.log-row {
  display: grid;
  grid-template-columns: 54px auto 1fr minmax(6em, auto);
  gap: 6px;
  align-items: baseline;
  padding: 2px 4px;
  border-left: 2px solid transparent;
}
.log-row:hover { background: rgba(255, 255, 255, 0.02); }
.log-row.sev-muted { opacity: 0.72; }
/* 一行 severity → 左边框 + [分类] + 结论 同色 */
.log-row.sev-detect  { border-left-color: rgba(45, 212, 191, 0.45); --log-tone: var(--teal-2); }
.log-row.sev-normal  { border-left-color: var(--lv-normal); --log-tone: var(--lv-normal); }
.log-row.sev-w1      { border-left-color: var(--lv-w1); --log-tone: var(--lv-w1); }
.log-row.sev-w2      { border-left-color: var(--lv-w2); --log-tone: var(--lv-w2); }
.log-row.sev-alarm   { border-left-color: var(--lv-alarm); --log-tone: var(--lv-alarm); }
.log-row.sev-pre,
.log-row.sev-trend   { border-left-color: var(--lv-pre); --log-tone: var(--lv-pre-2); }
.log-row.sev-diag    { border-left-color: #f0c674; --log-tone: #f0c674; }
.log-row.sev-agent   { border-left-color: #c4b5fd; --log-tone: #93c5fd; }
.log-row.sev-report  { border-left-color: #fda4af; --log-tone: #fda4af; }
.log-row.sev-muted   { border-left-color: rgba(160, 174, 192, 0.25); --log-tone: var(--fg-4); }
/* 气体行：[分类] 与数值同为正文色，左边框略提亮 */
.log-row.log-gas {
  --log-tone: var(--fg-2);
  border-left-color: rgba(160, 174, 192, 0.35);
}
.log-row .ts { font-size: 10px; color: var(--fg-4); }
.log-row .cat { color: var(--log-tone, var(--fg-3)); font-weight: 650; white-space: nowrap; }
.log-row .msg { color: var(--fg-2); min-width: 0; word-break: break-word; }
/* v-html 内节点无 scoped 标记，必须 :deep */
.log-row .msg :deep(.msg-dim) { color: var(--fg-4); font-weight: 500; }
.log-row .msg :deep(.msg-arrow) { margin: 0 4px; color: var(--fg-4); font-weight: 700; }
.log-row .msg :deep(.msg-result) { font-weight: 650; color: var(--fg-2); }
.log-row .msg :deep(.tone-detect) { color: var(--teal-2); }
.log-row .msg :deep(.tone-normal) { color: var(--lv-normal); }
.log-row .msg :deep(.tone-w1) { color: var(--lv-w1); }
.log-row .msg :deep(.tone-w2) { color: var(--lv-w2); }
.log-row .msg :deep(.tone-alarm) { color: var(--lv-alarm); }
.log-row .msg :deep(.tone-pre),
.log-row .msg :deep(.tone-trend) { color: var(--lv-pre-2); }
.log-row .msg :deep(.tone-diag) { color: #f0c674; }
.log-row .msg :deep(.tone-agent) { color: #93c5fd; }
.log-row .msg :deep(.tone-report) { color: #fda4af; }
.log-row .msg :deep(.tone-muted) { color: var(--fg-4); font-weight: 500; }
.log-row .msg :deep(.gas-unit) { font-size: 0.72em; font-weight: 500; opacity: 0.72; margin-left: 1px; }
.log-cites {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 4px 6px;
  text-align: right;
}
.log-cites :deep(.std-cite) { font-size: 10px; }

.output-row {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 12px;
  align-items: start;
}
@media (max-width: 1100px) {
  .output-row { grid-template-columns: 1fr; }
}

.g1-panel,
.decision-panel {
  align-self: start;
  height: auto;
}
.g1-panel .gp-body,
.decision-panel .gp-body {
  flex: 0 1 auto;
}

.g1-body { padding: 12px !important; }
.g1-preview {
  max-height: none;
  overflow: visible;
  background: #e8ecf0;
  border-radius: 8px;
  padding: 8px;
}
.opinion-mode-bar {
  font-family: system-ui, sans-serif;
  font-size: 11px;
  font-weight: 650;
  color: #334155;
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 6px 10px;
  margin-bottom: 8px;
}
.opinion-mode-bar.llm {
  color: #0f766e;
  border-color: rgba(45, 212, 191, 0.55);
  background: rgba(45, 212, 191, 0.12);
}
.opinion-mode-bar.rule_template {
  color: #92400e;
  border-color: #f59e0b;
  background: #fffbeb;
}
.opinion-mode-note {
  display: block;
  margin-top: 2px;
  font-weight: 500;
  font-size: 10px;
  opacity: 0.85;
}
.g1-preview.locked { opacity: 0.45; pointer-events: none; filter: grayscale(0.3); }
.g1-placeholder {
  padding: 28px; text-align: center; color: var(--fg-4); font-size: 12px;
  border: 1px dashed var(--line); border-radius: 8px;
  background: var(--bg-3);
}

.tag-mod {
  margin-left: auto; font-size: 10px; color: var(--teal-2);
  border: 1px solid rgba(45,212,191,0.3); padding: 1px 6px; border-radius: 4px;
}
.decision-body { display: flex; flex-direction: column; gap: 12px; position: relative; min-height: 160px; }
.dec-item { padding-bottom: 10px; border-bottom: 1px solid var(--line); }
.dec-item:last-child { border-bottom: none; padding-bottom: 0; }
.dec-k { font-size: 11px; color: var(--fg-4); }
.dec-v { font-size: 15px; font-weight: 700; color: var(--fg); margin: 4px 0; }
.dec-v.teal { color: var(--teal-2); }
.dec-v.agent { color: #93c5fd; }
.dec-v.w1 { color: var(--lv-w1); }
.dec-v.w2 { color: var(--lv-w2); }
.dec-v.alarm { color: var(--lv-alarm); }
.dec-v.pre { color: var(--lv-pre-2); }
.dec-v.normal { color: var(--lv-normal); }
.dec-s { font-size: 11px; color: var(--fg-4); line-height: 1.5; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.dec-basis-k {
  flex: 0 0 auto;
  font-size: 10px;
  font-weight: 700;
  color: var(--fg-3);
  letter-spacing: 0.04em;
}
.dec-why { color: var(--fg-3); flex: 1 1 12em; min-width: 0; }
.tp-top { margin-bottom: 10px; }
.tp-title {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  font-size: 11px; font-weight: 700; color: var(--fg-3); letter-spacing: 0.04em;
}
.tp-basis {
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
}
.tp-table-hint { color: var(--fg-3); }
.tp-block {
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--bg-3);
}
.tp-block:last-of-type { margin-bottom: 0; }
.tp-chain { margin: 0; }
.tp-row {
  display: grid;
  grid-template-columns: 4.5em 1fr;
  gap: 6px 10px;
  align-items: baseline;
  padding: 3px 0;
}
.tp-row dt {
  margin: 0;
  font-size: 11px; font-weight: 700; color: var(--fg-4);
}
.tp-row dd {
  margin: 0;
  font-size: 12.5px; color: var(--fg); line-height: 1.45;
  display: flex; flex-wrap: wrap; align-items: flex-start; gap: 6px;
}
.tp-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px; font-weight: 700;
  padding: 1px 6px; border-radius: 4px;
  background: rgba(45, 212, 191, 0.12);
  color: #5eead4;
  border: 1px solid rgba(45, 212, 191, 0.3);
  margin-right: 4px;
}
.tp-items {
  margin: 0;
  padding: 0 0 0 1.1em;
  width: 100%;
  list-style: disc;
  font-size: 12.5px; color: var(--fg-2); line-height: 1.65;
}
.tp-items li { margin: 0; }
.offline-note {
  margin: 8px 0 0;
  font-size: 10px;
  color: var(--fg-4);
  opacity: 0.8;
  line-height: 1.4;
}

.decision-lock {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  background: rgba(20,28,36,0.72); color: var(--fg-3); font-size: 12px;
  border-radius: var(--r);
}

/* 表 G.1 样式在 ReportCardG.vue；此处只管预览壳 */
.mode-pill {
  font-size: 11px; font-weight: 650; padding: 4px 10px; border-radius: 999px;
  border: 1px solid var(--line); color: var(--fg-3);
}
.mode-pill.llm { border-color: rgba(45, 212, 191, 0.45); color: #5eead4; background: rgba(45, 212, 191, 0.08); }
.mode-pill.rule_template { background: var(--bg-3); }

.modal {
  position: fixed; inset: 0; z-index: 90;
  display: flex; align-items: center; justify-content: center;
}
.modal-backdrop { position: absolute; inset: 0; background: rgba(0,0,0,0.55); }
.modal-dialog {
  position: relative;
  width: min(980px, calc(100vw - 24px));
  max-height: calc(100vh - 40px);
  overflow: hidden; display: flex; flex-direction: column;
  border-radius: var(--r-lg); border: 1px solid var(--line);
  background: var(--bg-2); box-shadow: 0 16px 48px rgba(0,0,0,0.45);
}
.modal-head {
  display: flex; justify-content: space-between; gap: 12px;
  padding: 14px 16px; border-bottom: 1px solid var(--line);
}
.modal-head h3 { margin: 0 0 4px; font-size: 15px; }
.modal-meta { font-size: 11px; color: var(--fg-4); display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.modal-grade {
  font-size: 10px; font-weight: 700; padding: 1px 8px; border-radius: 999px;
  border: 1px solid var(--line);
}
.modal-grade.normal { color: var(--lv-normal); }
.modal-grade.w1 { color: #fbbf24; }
.modal-grade.w2 { color: #fdba74; }
.modal-grade.alarm { color: #fca5a5; }
.modal-x { border: none; background: transparent; color: var(--fg-3); font-size: 22px; cursor: pointer; }
.modal-body { padding: 14px 16px; overflow-y: auto; background: #e8ecf0; }
.modal-foot {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 12px 16px; border-top: 1px solid var(--line);
}

.toolbar :deep(.el-input__wrapper),
.toolbar :deep(.el-select__wrapper) {
  background: var(--bg-3) !important;
  box-shadow: 0 0 0 1px var(--line-2) inset !important;
}
.toolbar :deep(.el-input__inner),
.toolbar :deep(.el-select__selected-item) { color: var(--fg) !important; }
</style>
