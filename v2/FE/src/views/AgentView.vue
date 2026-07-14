<script setup>
// Agent 编排 —— 竖向七步流程 + 依据日志 + 表G.1 + 监测决策
// 判定全由国标规则;Agent B 优先 LLM 写人话,失败/无密钥降级规则模板
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import http from '@/service/http'
import StdCite from '@/components/StdCite.vue'
import ReportCardG from '@/components/ReportCardG.vue'

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

/** Agent 试验区：当前状态 / 依据表 / 建议试验（附录D·辅助判断或停电测试） */
function stripClauseFromName(test, clause) {
  if (!test) return ''
  let s = String(test)
  if (clause) s = s.replace(`(${clause})`, '')
  s = s.replace(/\(B\.[^)]+\)/g, '')
  return s.trim()
}

const agentTrials = computed(() => {
  const d = decision.value
  if (!d) return null
  const basis = (d.trials_basis || []).find((b) => b.cite === '722-附录D' || b.label === '附录D')
  const nature = d.trials_nature_label || '—'
  const verify = d.trials_purpose === 'verify'
  const primary = (basis?.status || '')
    .replace(/^当前状况：/, '')
    .replace(/^暂定/, '')
    .replace(/^「[^」]+」\s*[·・]?\s*/, '')
    .replace(/（[^）]*）$/, '')
    .trim()
  const status = verify
    ? `故障性质暂定为「${nature}」${primary ? `（${primary}）` : ''}`
    : `故障性质为「${nature}」${primary ? `（${primary}）` : ''}`
  const dNames = d.trials_appendix_d?.length
    ? d.trials_appendix_d
    : (d.trials || []).filter((t) => !/\(B\./.test(t))
  const bChains = (d.trials_1685_items || []).map((it) => ({
    status: it.why || '当日气体组合贴近附录B状态量描述',
    table: `1685 表${it.clause || 'B'}`,
    cite: '1685-附录B',
    suggest: stripClauseFromName(it.test, it.clause),
    badge: it.clause || '',
  }))
  return {
    verify,
    title: verify ? '核实试验' : '建议试验',
    major: dNames.length ? {
      status,
      table: `722 表D.1「${nature}」列`,
      cite: '722-附录D',
      suggest: verify
        ? `建议下列停电测试 / 辅助判断项目（共 ${dNames.length} 项，仅核实、不作确诊）`
        : `建议下列停电测试 / 辅助判断项目（共 ${dNames.length} 项）`,
      items: dNames,
    } : null,
    details: bChains,
    empty: !dNames.length && !bChains.length,
  }
})
const g1 = computed(() => result.value?.g1 || null)
const g2 = computed(() => result.value?.g2 || null)
const reportMode = computed(() => result.value?.mode || 'rule_template')
const knowledgeFlat = computed(() => g1.value?.cite_ids || [])
const modeLabel = computed(() => (reportMode.value === 'llm' ? 'LLM' : '规则模板'))

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

const eligibleDates = computed(() => series.value.filter((s) => s.eligible).map((s) => s.date))
const idx = computed(() => series.value.findIndex((s) => s.date === selectedDate.value))

const gradeClass = (g) => ({
  正常: 'normal', 注意值1: 'w1', 注意值2: 'w2', 告警值: 'alarm',
}[g] || 'normal')

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
  // 可判型日与判型页同用高亮；其余按档位标色
  if (hit.eligible) return 'ag-eligible'
  if (hit.grade === '注意值1') return 'ag-w1'
  if (hit.is_pre) return 'ag-pre'
  return ''
}
function stepDay(delta) {
  if (running.value) return
  const i = idx.value + delta
  if (i < 0 || i >= series.value.length) return
  selectedDate.value = series.value[i].date
}
function jumpEligible(dir) {
  if (running.value) return
  const list = eligibleDates.value
  if (!list.length) return
  const cur = selectedDate.value
  if (dir < 0) {
    selectedDate.value = [...list].reverse().find((d) => d < cur) || list[list.length - 1]
  } else {
    selectedDate.value = list.find((d) => d > cur) || list[0]
  }
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

/** 日志结论高亮：箭头后的部分换色 */
function splitLog(msg) {
  const m = String(msg || '').match(/^(.*?)(→|->)(.*)$/s)
  if (!m) return { head: msg, arrow: '', result: '' }
  return { head: m[1], arrow: m[2], result: m[3].trim() }
}

/** 结论色跟档位/紧急度/可信度走，不跟步骤模块走 */
function inferSeverity(step) {
  const id = step?.id || ''
  const d = step?.detail || {}
  if (id === 'grade') return gradeTone(d.grade)
  if (id === 'urgency') {
    if (d.is_pre) return 'pre'
    const lv = d.urgency?.level
    if (lv === '高') return 'alarm'
    if (lv === '中') return 'w2'
    if (lv === '低') return 'w1'
    return 'muted'
  }
  if (id === 'diagnose') {
    const diag = d.diagnosis || {}
    if (!diag.triggered) return 'muted'
    const conf = diag.fusion?.confidence || d.fusion?.confidence
    if (conf === '低') return 'w1'
    if (conf === '高') return 'w2'
    return 'diag'
  }
  if (id === 'trend') {
    if (d.is_pre) return 'pre'
    if (d.thc_rel_rate != null && d.thc_rel_rate >= 10) return 'w1'
    return 'muted'
  }
  if (id === 'decide') {
    const g = result.value?.grade
    if (g === '告警值') return 'alarm'
    if (g === '注意值2') return 'w2'
    if (result.value?.is_pre) return 'pre'
    if (g === '注意值1') return 'w1'
    return 'agent'
  }
  if (id === 'report') return 'report'
  return 'muted'
}

function gradeTone(g) {
  return ({
    正常: 'normal', 注意值1: 'w1', 注意值2: 'w2', 告警值: 'alarm',
  })[g] || 'muted'
}

function decisionTone() {
  const g = result.value?.grade
  if (g === '告警值') return 'alarm'
  if (g === '注意值2') return 'w2'
  if (result.value?.is_pre) return 'pre'
  if (g === '注意值1') return 'w1'
  return 'teal'
}

async function loadSeries() {
  const res = await http.get('/agent/series')
  series.value = res.series || []
  summary.value = res.summary || {}
  const q = typeof route.query.date === 'string' ? route.query.date : ''
  const fallback = res.summary?.default_date || series.value.at(-1)?.date
  selectedDate.value = (q && series.value.some((s) => s.date === q)) ? q : fallback
}

function applyQueryDate() {
  const q = typeof route.query.date === 'string' ? route.query.date : ''
  if (!q || !series.value.some((s) => s.date === q)) return
  pendingOpenReport.value = true
  if (selectedDate.value !== q) {
    selectedDate.value = q // watch → runAgent
  } else if (!running.value) {
    runAgent().then(() => {
      if (pendingOpenReport.value && reportReady.value) {
        modalOpen.value = true
        pendingOpenReport.value = false
      }
    })
  }
}

function periodCiteLabel(id) {
  return ({
    '1498-A.3.1': 'A.3.1',
    '1498-5.5.5': '§5.5.5',
    '1498-5.4.5': '§5.4.5',
    '722-9.3.3': '§9.3.3',
    '722-5.4.5': '§5.4.5',
    '722-5.4': '§5.4',
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

async function runAgent() {
  if (running.value || !selectedDate.value) return
  running.value = true
  resetUi()
  try {
    const data = await http.get('/agent/run', { day: selectedDate.value })
    result.value = data
    await playSteps(data.steps || [])
    reportReady.value = true
  } catch (e) {
    result.value = null
    reportReady.value = false
    logs.value.push({
      ts: nowTs(),
      label: '错误',
      tag: 'agent',
      msg: e?.message || String(e),
      cite: null,
    })
  } finally {
    running.value = false
  }
}

async function playSteps(list) {
  for (let i = 0; i < list.length; i++) {
    if (i > 0) doneUpTo.value = i
    activeIdx.value = i
    const s = list[i]
    logs.value.push({
      ts: nowTs(),
      label: s.label,
      tag: s.tag,
      severity: inferSeverity(s),
      msg: s.log,
      ...splitLog(s.log),
      cite: s.cite,
    })
    await nextTick()
    const el = document.getElementById('agent-log')
    if (el) el.scrollTop = el.scrollHeight
    await sleep(i === list.length - 1 ? 700 : 550)
  }
  doneUpTo.value = list.length
  activeIdx.value = -1
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

const bootReady = ref(false)
const pendingOpenReport = ref(false)

onMounted(async () => {
  try {
    await loadSeries()
  } finally {
    loading.value = false
  }
  // 进入页即跑当日编排；带 ?date=（告警摘要跳转）再自动打开完整报告弹层
  if (selectedDate.value) {
    await runAgent()
    if (typeof route.query.date === 'string' && route.query.date && reportReady.value) {
      modalOpen.value = true
    }
  }
  bootReady.value = true
})

watch(
  () => route.query.date,
  (q, prev) => {
    if (!bootReady.value || q === prev) return
    applyQueryDate()
  },
)

// 日期变更（日历 / 可判型跳转）自动重跑
watch(selectedDate, async (d, prev) => {
  if (!bootReady.value || !d || d === prev || running.value) return
  await runAgent()
  if (pendingOpenReport.value && reportReady.value) {
    modalOpen.value = true
    pendingOpenReport.value = false
  }
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
            :disabled="running"
            class="date-pick"
          />
          <button
            type="button"
            class="btn btn-ghost"
            :disabled="running || idx < 0 || idx >= series.length - 1"
            @click="stepDay(1)"
          >后日 ›</button>
        </div>
        <div class="nav">
          <button
            type="button"
            class="btn btn-ghost"
            :disabled="running || !eligibleDates.length"
            @click="jumpEligible(-1)"
          >‹ 上一可判型</button>
          <el-select
            v-model="selectedDate"
            filterable
            placeholder="跳到可判型日"
            class="eligible-select"
            :disabled="running || !eligibleDates.length"
          >
            <el-option v-for="d in eligibleDates" :key="d" :label="d" :value="d" />
          </el-select>
          <button
            type="button"
            class="btn btn-ghost"
            :disabled="running || !eligibleDates.length"
            @click="jumpEligible(1)"
          >下一可判型 ›</button>
        </div>
        <span class="meta">可判型 {{ summary.eligible_days ?? eligibleDates.length }}/{{ summary.total_days ?? series.length }}</span>
        <div class="actions">
          <span v-if="reportReady" class="mode-pill" :class="reportMode">
            Agent B · {{ reportMode === 'llm' ? 'LLM 人话' : '规则模板' }}
          </span>
          <button type="button" class="btn btn-ghost" :disabled="!reportReady" @click="openReport">
            完整报告
          </button>
          <button type="button" class="btn btn-primary" :disabled="running || !selectedDate" @click="runAgent">
            {{ running ? '运行中…' : reportReady ? '重新运行' : '运行 Agent' }}
          </button>
        </div>
      </div>
    </div>

    <div class="agent-layout">
      <!-- 左：竖向七步 -->
      <section class="gp flow-panel">
        <div class="gp-head">
          分析流程
          <StdCite ref-id="722-10.3" label="§10.3" />
        </div>
        <div class="gp-body flow-body">
          <div class="v-pipeline">
            <div
              v-for="(s, i) in (steps.length ? steps : [
                { label: '时序输入', sub: '360 天合成时序 · SYN-001' },
                { label: '四档分级', sub: 'DL/T 1498.2 表 A.3' },
                { label: '处置紧急度', sub: '产气速率 · §9.3.3' },
                { label: '故障类型', sub: '三比值法 · Duval · 特征气体' },
                { label: '产气趋势', sub: '「预」提前预警 · 产气涨势' },
                { label: 'Agent 决策', sub: '模块 B 报告 + 模块 C 监测' },
                { label: '表 G.1/G.2 报告', sub: '附录 G 档案卡片 · 分析意见' },
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
                  <StdCite
                    v-if="s.cite"
                    class="step-cite"
                    :ref-id="s.cite.id"
                    :label="s.cite.label"
                    inline
                  />
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
            <span class="head-hint">每步结论带国标依据</span>
          </div>
          <div id="agent-log" class="gp-body log-body">
            <div v-if="!logs.length" class="log-empty">点击「运行 Agent」开始编排</div>
            <div v-for="(line, i) in logs" :key="i" class="log-line" :class="'sev-' + (line.severity || 'muted')">
              <span class="ts">{{ line.ts }}</span>
              <span class="tag" :class="line.tag">{{ line.label }}</span>
              <span class="msg">
                <template v-if="line.result">
                  <span class="msg-head">{{ line.head }}</span>
                  <span class="msg-arrow">{{ line.arrow }}</span>
                  <span class="msg-result" :class="'tone-' + (line.severity || 'muted')">{{ line.result }}</span>
                </template>
                <template v-else>
                  <span class="msg-result" :class="'tone-' + (line.severity || 'muted')">{{ line.msg }}</span>
                </template>
              </span>
              <StdCite
                v-if="line.cite"
                class="log-cite"
                :ref-id="line.cite.id"
                :label="'依据 ' + line.cite.label"
                inline
              />
            </div>
          </div>
        </section>

        <div class="output-row">
          <section class="gp g1-panel">
            <div class="gp-head">
              输出预览 · 表 G.1 / G.2
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
                />
                <div v-else class="g1-placeholder">流程完成后解锁表 G.1 / G.2 预览</div>
                <div v-if="g1 && knowledgeFlat.length" class="cite-row preview-cites">
                  <span class="cite-k">依据</span>
                  <StdCite
                    v-for="cid in knowledgeFlat"
                    :key="cid"
                    :ref-id="cid"
                    :label="cid"
                    inline
                  />
                </div>
              </div>
            </div>
          </section>

          <section class="gp decision-panel">
            <div class="gp-head">
              监测决策
              <span class="tag-mod">模块 C</span>
            </div>
            <div class="gp-body decision-body">
              <template v-if="reportReady && decision">
                <div class="dec-item">
                  <div class="dec-k">建议检测周期</div>
                  <div class="dec-v" :class="decisionTone()">{{ decision.period }}</div>
                  <div class="dec-s">
                    {{ decision.period_sub }}
                    <StdCite
                      :ref-id="decision.cite_period"
                      :label="periodCiteLabel(decision.cite_period)"
                      inline
                    />
                  </div>
                </div>
                <div class="dec-item">
                  <div class="dec-k">二次采样</div>
                  <div class="dec-v">{{ decision.resample }}</div>
                  <div class="dec-s">
                    {{ decision.resample_sub }}
                    <StdCite
                      :ref-id="decision.cite_resample || '1498-5.4.5'"
                      :label="periodCiteLabel(decision.cite_resample || '1498-5.4.5')"
                      inline
                    />
                  </div>
                </div>
                <div class="dec-item trials-panel" :class="{ verify: agentTrials?.verify }">
                  <div class="tp-top">
                    <div class="tp-title">
                      {{ agentTrials?.title || '试验' }}
                      <span v-if="agentTrials?.verify" class="tp-tag">仅核实</span>
                    </div>
                  </div>

                  <template v-if="agentTrials && !agentTrials.empty">
                    <!-- 大类：状态 / 表 / 结论 + 清单 -->
                    <div v-if="agentTrials.major" class="tp-block">
                      <dl class="tp-chain">
                        <div class="tp-row">
                          <dt>当前状态</dt>
                          <dd>{{ agentTrials.major.status }}</dd>
                        </div>
                        <div class="tp-row">
                          <dt>依据表</dt>
                          <dd>
                            {{ agentTrials.major.table }}
                            <StdCite :ref-id="agentTrials.major.cite" :label="agentTrials.major.cite" inline />
                          </dd>
                        </div>
                        <div class="tp-row">
                          <dt>建议试验</dt>
                          <dd>{{ agentTrials.major.suggest }}</dd>
                        </div>
                      </dl>
                      <ul class="tp-items">
                        <li v-for="(name, i) in agentTrials.major.items" :key="'d'+i">{{ name }}</li>
                      </ul>
                    </div>

                    <!-- 细化：每条都写清三要素 -->
                    <div v-for="(ch, i) in agentTrials.details" :key="'b'+i" class="tp-block">
                      <dl class="tp-chain">
                        <div class="tp-row">
                          <dt>当前状态</dt>
                          <dd>{{ ch.status }}</dd>
                        </div>
                        <div class="tp-row">
                          <dt>依据表</dt>
                          <dd>
                            {{ ch.table }}
                            <StdCite :ref-id="ch.cite" :label="ch.cite" inline />
                          </dd>
                        </div>
                        <div class="tp-row">
                          <dt>建议试验</dt>
                          <dd>
                            <span v-if="ch.badge" class="tp-badge">{{ ch.badge }}</span>
                            {{ ch.suggest }}
                          </dd>
                        </div>
                      </dl>
                    </div>
                  </template>
                  <div v-else class="dec-s">—（未触发判型或无对应措施）</div>
                </div>
                <p v-if="decision.offline_note" class="offline-note" :title="decision.offline_note">
                  离线例行对照不写入在线主规则
                </p>
              </template>
              <div v-else class="decision-lock">等待流程完成</div>
            </div>
          </section>
        </div>
      </div>
    </div>

    <!-- 完整报告弹层：国标表 G.1 + 表 G.2 -->
    <div v-if="modalOpen && g1" class="modal">
      <div class="modal-backdrop" @click="closeReport" />
      <div class="modal-dialog" role="dialog">
        <div class="modal-head">
          <div>
            <h3>完整分析报告</h3>
            <div class="modal-meta">
              {{ g1.report_no }} · DL/T 722 附录 G 表 G.1 / G.2 · {{ modeLabel }}
              <span v-if="result?.grade" class="modal-grade" :class="gradeClass(result.grade)">
                {{ result.grade }}
              </span>
            </div>
          </div>
          <button type="button" class="modal-x" @click="closeReport">×</button>
        </div>
        <div class="modal-body">
          <ReportCardG :g1="g1" :g2="g2" mode="full" />
          <div v-if="knowledgeFlat.length" class="cite-row modal-cites">
            <span class="cite-k">依据角标</span>
            <StdCite
              v-for="cid in knowledgeFlat"
              :key="'m'+cid"
              :ref-id="cid"
              :label="cid"
              inline
            />
          </div>
        </div>
        <div class="modal-foot">
          <button type="button" class="btn btn-primary" @click="closeReport">关闭</button>
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
.eligible-select { width: 160px; }
.meta { font-size: 12px; color: var(--fg-3); }
.actions { display: flex; gap: 8px; margin-left: auto; align-items: center; }
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

.flow-panel { display: flex; flex-direction: column; min-height: 0; }
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

.flow-progress { margin-top: auto; padding-top: 8px; }
.bar { height: 4px; border-radius: 2px; background: var(--bg-3); overflow: hidden; }
.fill { height: 100%; background: linear-gradient(90deg, var(--teal), #d4a017); transition: width 0.35s; }
.meta {
  display: flex; justify-content: space-between;
  margin-top: 6px; font-size: 11px; color: var(--fg-4);
}

.main-col { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.log-panel { flex: 1; min-height: 180px; display: flex; flex-direction: column; }
.head-hint { margin-left: auto; font-size: 10px; color: var(--fg-4); font-weight: 500; }
.log-body {
  max-height: 280px; overflow-y: auto;
  display: flex; flex-direction: column; gap: 8px;
  font-size: 12px;
}
.log-empty { color: var(--fg-4); padding: 20px 0; text-align: center; }
.log-line {
  display: grid;
  grid-template-columns: 54px auto 1fr auto;
  gap: 8px; align-items: start;
  padding: 8px 10px; border-radius: 6px; background: var(--bg-3);
  border-left: 3px solid transparent;
}
.log-line.sev-normal { border-left-color: var(--lv-normal); }
.log-line.sev-w1 { border-left-color: var(--lv-w1); }
.log-line.sev-w2 { border-left-color: var(--lv-w2); }
.log-line.sev-alarm { border-left-color: var(--lv-alarm); }
.log-line.sev-pre { border-left-color: #67e8f9; }
.log-line.sev-diag { border-left-color: #f0c674; }
.log-line.sev-agent { border-left-color: #c4b5fd; }
.log-line.sev-report { border-left-color: #fda4af; }
.log-line.sev-muted { border-left-color: rgba(160,174,192,0.35); }
.ts { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--fg-4); }
.tag {
  font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 4px;
  background: var(--bg-2); color: var(--fg-3); white-space: nowrap;
}
.tag.detect { color: var(--teal-2); }
.tag.diag { color: #f0c674; }
.tag.trend { color: #7dd3fc; }
.tag.agent { color: #c4b5fd; }
.tag.report { color: #fda4af; }
.msg { color: var(--fg-3); line-height: 1.45; }
.msg-head { color: var(--fg-3); }
.msg-arrow { margin: 0 4px; color: var(--fg-4); }
.msg-result { font-weight: 700; }
.tone-normal { color: var(--lv-normal); }
.tone-w1 { color: var(--lv-w1); }
.tone-w2 { color: var(--lv-w2); }
.tone-alarm { color: var(--lv-alarm); }
.tone-pre { color: #67e8f9; }
.tone-diag { color: #f0c674; }
.tone-agent { color: #c4b5fd; }
.tone-report { color: #fda4af; }
.tone-muted { color: var(--fg-3); font-weight: 600; }
.log-cite { white-space: nowrap; }

.output-row {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 12px;
}
@media (max-width: 1100px) {
  .output-row { grid-template-columns: 1fr; }
}

.g1-body { padding: 12px !important; }
.g1-preview {
  max-height: 420px;
  overflow: auto;
  background: #e8ecf0;
  border-radius: 8px;
  padding: 8px;
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
.dec-v.w1 { color: var(--lv-w1); }
.dec-v.w2 { color: var(--lv-w2); }
.dec-v.alarm { color: var(--lv-alarm); }
.dec-v.pre { color: #67e8f9; }
.dec-v.normal { color: var(--lv-normal); }
.dec-s { font-size: 11px; color: var(--fg-4); line-height: 1.5; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.trials-panel.verify {
  border-left: 2px solid rgba(251, 191, 36, 0.45);
  padding-left: 10px;
}
.tp-top { margin-bottom: 10px; }
.tp-title {
  display: flex; align-items: center; gap: 8px;
  font-size: 11px; font-weight: 700; color: var(--fg-3); letter-spacing: 0.04em;
}
.tp-tag {
  font-size: 10px; font-weight: 700; padding: 1px 7px; border-radius: 999px;
  background: rgba(251, 191, 36, 0.12); color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.35);
}
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
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
}
.tp-row dd.mono {
  font-family: inherit;
  font-size: 12.5px; color: var(--fg-2);
}
.tp-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px; font-weight: 700;
  padding: 1px 6px; border-radius: 4px;
  background: rgba(45, 212, 191, 0.12);
  color: #5eead4;
  border: 1px solid rgba(45, 212, 191, 0.3);
}
.tp-items {
  margin: 8px 0 0;
  padding: 8px 0 0 1.1em;
  border-top: 1px dashed var(--line);
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

/* 表 G.1 样式在 ReportCardG.vue；此处只管预览壳 + 角标 */
.cite-row {
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px 8px;
  margin-top: 8px; padding-top: 6px; border-top: 1px dashed var(--line);
}
.preview-cites { border-top-color: rgba(0,0,0,0.15); }
.preview-cites .cite-k { color: #666; }
.modal-cites { margin-top: 12px; border-top-color: var(--line); }
.cite-k { font-size: 10px; color: var(--fg-4); font-weight: 650; }
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
.modal-grade.normal { color: #86efac; }
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

<style>
.el-date-table td.ag-eligible .el-date-table-cell__text {
  background: rgba(45, 212, 191, 0.22) !important;
  color: #5eead4 !important;
  border-radius: 50%;
}
.el-date-table td.ag-w1 .el-date-table-cell__text {
  box-shadow: inset 0 -2px 0 #fbbf24;
}
.el-date-table td.ag-pre .el-date-table-cell__text {
  box-shadow: inset 0 -2px 0 #67e8f9;
}
</style>
