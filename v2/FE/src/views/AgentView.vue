<script setup>
// Agent 编排 —— 竖向七步流程 + 依据日志 + 表G.1 + 监测决策
// 判定全由国标规则;本版分析意见/决策为规则模板(LLM 降级)
import { ref, computed, onMounted, nextTick } from 'vue'
import http from '@/service/http'
import StdCite from '@/components/StdCite.vue'

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
const g1 = computed(() => result.value?.g1 || null)

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
  if (hit.grade === '告警值') return 'ag-alarm'
  if (hit.grade === '注意值2') return 'ag-w2'
  if (hit.grade === '注意值1') return 'ag-w1'
  if (hit.is_pre) return 'ag-pre'
  return ''
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

function gasTone(gas, v) {
  if (v == null) return 'empty'
  if (gas === 'c2h2') {
    if (v >= 5) return 'over'
    if (v >= 1) return 'warn'
  }
  if (gas === 'h2' || gas === 'thc') {
    if (v >= 150) return 'warn'
  }
  return ''
}

function fmtGas(v) {
  return v == null ? '—' : v
}

/** 日志结论高亮：箭头后的部分换色 */
function splitLog(msg) {
  const m = String(msg || '').match(/^(.*?)(→|->)(.*)$/s)
  if (!m) return { head: msg, arrow: '', result: '' }
  return { head: m[1], arrow: m[2], result: m[3].trim() }
}

/** 可判型日快捷：不与当前日强绑（非可判型日会显示空白） */
const jumpEligible = ref('')
function onJumpEligible(e) {
  const d = e.target.value
  if (d) {
    selectedDate.value = d
    jumpEligible.value = ''
  }
}

async function loadSeries() {
  const res = await http.get('/agent/series')
  series.value = res.series || []
  summary.value = res.summary || {}
  selectedDate.value = res.summary?.default_date || series.value.at(-1)?.date
}

function resetUi() {
  activeIdx.value = -1
  doneUpTo.value = -1
  logs.value = []
  reportReady.value = false
  modalOpen.value = false
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

onMounted(async () => {
  try {
    await loadSeries()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div v-loading="loading" class="agent">
    <div class="gp toolbar-card">
      <div class="gp-body toolbar">
        <div class="nav">
          <span class="lbl">监测日</span>
          <el-date-picker
            v-model="selectedDate"
            type="date"
            value-format="YYYY-MM-DD"
            :disabled-date="disabledDate"
            :cell-class-name="cellClassName"
            :disabled="running"
            class="date-pick"
          />
          <label class="jump">
            <span class="lbl">跳转可判型日</span>
            <select
              :value="jumpEligible"
              class="elig-select"
              :disabled="running || !eligibleDates.length"
              @change="onJumpEligible"
            >
              <option value="">注意值2+ 共 {{ eligibleDates.length }} 天…</option>
              <option v-for="d in eligibleDates" :key="d" :value="d">{{ d }}</option>
            </select>
          </label>
        </div>
        <div class="actions">
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
                { label: '表 G.1 报告', sub: '附录 G 档案卡片 · 分析意见' },
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
            <div v-for="(line, i) in logs" :key="i" class="log-line">
              <span class="ts">{{ line.ts }}</span>
              <span class="tag" :class="line.tag">{{ line.label }}</span>
              <span class="msg" :class="'tone-' + line.tag">
                <template v-if="line.result">
                  <span class="msg-head">{{ line.head }}</span>
                  <span class="msg-arrow">{{ line.arrow }}</span>
                  <span class="msg-result">{{ line.result }}</span>
                </template>
                <template v-else>{{ line.msg }}</template>
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
              输出预览 · 表 G.1
              <button type="button" class="btn btn-ghost mini" :disabled="!reportReady" @click="openReport">
                完整报告
              </button>
            </div>
            <div class="gp-body g1-body">
              <div class="g1-preview" :class="reportReady ? 'unlocked' : 'locked'">
                <div v-if="g1" class="g1-sheet compact">
                  <div class="g1-title">表 G.1 油中溶解气体分析档案卡片</div>
                  <div class="g1-meta">
                    <div class="g1-meta-left">局（厂、所）：<span class="g1-meta-line" /></div>
                    <div class="g1-meta-right">编号：<span class="g1-meta-no">{{ g1.report_no }}</span></div>
                  </div>
                  <table class="g1-table">
                    <tr>
                      <td class="g1-lbl">电压等级</td>
                      <td class="g1-val">{{ g1.voltage }}</td>
                      <td class="g1-lbl">出厂序号</td>
                      <td class="g1-val">{{ g1.device_id }}</td>
                      <td class="g1-lbl">当日最高档</td>
                      <td class="g1-val" :class="gradeClass(result?.grade)">{{ result?.grade }}</td>
                    </tr>
                    <tr>
                      <td class="g1-lbl">取样日期</td>
                      <td class="g1-val" colspan="5">
                        {{ (g1.sample_dates || []).filter(Boolean).join(' · ') || '—' }}
                      </td>
                    </tr>
                    <tr>
                      <td class="g1-lbl">H₂</td>
                      <td class="g1-val" :class="gasTone('h2', g1.gases?.h2?.[0])">{{ fmtGas(g1.gases?.h2?.[0]) }}</td>
                      <td class="g1-lbl">C₂H₂</td>
                      <td class="g1-val" :class="gasTone('c2h2', g1.gases?.c2h2?.[0])">{{ fmtGas(g1.gases?.c2h2?.[0]) }}</td>
                      <td class="g1-lbl">总烃</td>
                      <td class="g1-val" :class="gasTone('thc', g1.gases?.thc?.[0])">{{ fmtGas(g1.gases?.thc?.[0]) }}</td>
                    </tr>
                    <tr>
                      <td class="g1-lbl">分析意见</td>
                      <td class="g1-opinion" colspan="5">{{ g1.opinion }}</td>
                    </tr>
                  </table>
                </div>
                <div v-else class="g1-placeholder">流程完成后解锁表 G.1 预览</div>
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
                  <div class="dec-v teal">{{ decision.period }}</div>
                  <div class="dec-s">
                    {{ decision.period_sub }}
                    <StdCite :ref-id="decision.cite_period" :label="decision.cite_period === '722-9.3.3' ? '§9.3.3' : '§5.4'" inline />
                  </div>
                </div>
                <div class="dec-item">
                  <div class="dec-k">二次采样</div>
                  <div class="dec-v">{{ decision.resample }}</div>
                  <div class="dec-s">
                    {{ decision.resample_sub }}
                    <StdCite ref-id="722-5.4.5" label="§5.4.5" inline />
                  </div>
                </div>
                <div class="dec-item">
                  <div class="dec-k">附录 D 试验</div>
                  <ul v-if="decision.trials?.length" class="trial-list">
                    <li v-for="(t, i) in decision.trials" :key="i">{{ t }}</li>
                  </ul>
                  <div v-else class="dec-s">—（未触发判型或无对应措施）</div>
                </div>
              </template>
              <div v-else class="decision-lock">等待流程完成</div>
            </div>
          </section>
        </div>
      </div>
    </div>

    <!-- 完整报告弹层 -->
    <div v-if="modalOpen && g1" class="modal">
      <div class="modal-backdrop" @click="closeReport" />
      <div class="modal-dialog" role="dialog">
        <div class="modal-head">
          <div>
            <h3>完整分析报告</h3>
            <div class="modal-meta">{{ g1.report_no }} · DL/T 722 附录 G 表 G.1 · 规则模板</div>
          </div>
          <button type="button" class="modal-x" @click="closeReport">×</button>
        </div>
        <div class="modal-body">
          <div class="g1-sheet">
            <div class="g1-title">表 G.1 油中溶解气体分析档案卡片</div>
            <div class="g1-meta">
              <div class="g1-meta-left">局（厂、所）：<span class="g1-meta-line" /></div>
              <div class="g1-meta-right">编号：<span class="g1-meta-no">{{ g1.report_no }}</span></div>
            </div>
            <table class="g1-table">
              <tr>
                <td class="g1-lbl">型号</td><td class="g1-val empty">—（合成虚拟设备，无铭牌）</td>
                <td class="g1-lbl">电压等级/容量</td><td class="g1-val">{{ g1.voltage }}</td>
                <td class="g1-lbl">油重, t</td><td class="g1-val empty">—</td>
                <td class="g1-lbl">油种</td><td class="g1-val empty">—</td>
              </tr>
              <tr>
                <td class="g1-lbl">制造厂</td><td class="g1-val empty">—</td>
                <td class="g1-lbl">出厂序号</td><td class="g1-val">{{ g1.device_id }}</td>
                <td class="g1-lbl">出厂年月</td><td class="g1-val empty">—</td>
                <td class="g1-lbl">投运日期</td><td class="g1-val empty">—</td>
              </tr>
              <tr>
                <td class="g1-section" rowspan="2">取样条件</td>
                <td class="g1-sub">年、月、日</td>
                <td class="g1-val" colspan="2">{{ g1.sample_dates?.[0] || '—' }}</td>
                <td class="g1-val" colspan="2">{{ g1.sample_dates?.[1] || '—' }}</td>
                <td class="g1-val">{{ g1.sample_dates?.[2] || '—' }}</td>
                <td class="g1-val empty">—</td>
              </tr>
              <tr>
                <td class="g1-sub">取样原因</td>
                <td class="g1-val empty" colspan="6">—（合成数据无此工况）</td>
              </tr>
              <tr>
                <td class="g1-section" rowspan="6">组分含量<br>μL/L</td>
                <td class="g1-sub">H₂</td>
                <td class="g1-val" :class="gasTone('h2', g1.gases?.h2?.[0])" colspan="2">{{ fmtGas(g1.gases?.h2?.[0]) }}</td>
                <td class="g1-val" colspan="2">{{ fmtGas(g1.gases?.h2?.[1]) }}</td>
                <td class="g1-val">{{ fmtGas(g1.gases?.h2?.[2]) }}</td>
                <td class="g1-val empty">—</td>
              </tr>
              <tr>
                <td class="g1-sub">CH₄</td>
                <td class="g1-val" colspan="2">{{ fmtGas(g1.gases?.ch4?.[0]) }}</td>
                <td class="g1-val" colspan="2">{{ fmtGas(g1.gases?.ch4?.[1]) }}</td>
                <td class="g1-val">{{ fmtGas(g1.gases?.ch4?.[2]) }}</td>
                <td class="g1-val empty">—</td>
              </tr>
              <tr>
                <td class="g1-sub">C₂H₄</td>
                <td class="g1-val" colspan="2">{{ fmtGas(g1.gases?.c2h4?.[0]) }}</td>
                <td class="g1-val" colspan="2">{{ fmtGas(g1.gases?.c2h4?.[1]) }}</td>
                <td class="g1-val">{{ fmtGas(g1.gases?.c2h4?.[2]) }}</td>
                <td class="g1-val empty">—</td>
              </tr>
              <tr>
                <td class="g1-sub">C₂H₆</td>
                <td class="g1-val" colspan="2">{{ fmtGas(g1.gases?.c2h6?.[0]) }}</td>
                <td class="g1-val" colspan="2">{{ fmtGas(g1.gases?.c2h6?.[1]) }}</td>
                <td class="g1-val">{{ fmtGas(g1.gases?.c2h6?.[2]) }}</td>
                <td class="g1-val empty">—</td>
              </tr>
              <tr>
                <td class="g1-sub">C₂H₂</td>
                <td class="g1-val" :class="gasTone('c2h2', g1.gases?.c2h2?.[0])" colspan="2">{{ fmtGas(g1.gases?.c2h2?.[0]) }}</td>
                <td class="g1-val" colspan="2">{{ fmtGas(g1.gases?.c2h2?.[1]) }}</td>
                <td class="g1-val">{{ fmtGas(g1.gases?.c2h2?.[2]) }}</td>
                <td class="g1-val empty">—</td>
              </tr>
              <tr>
                <td class="g1-sub">C₁+C₂</td>
                <td class="g1-val" :class="gasTone('thc', g1.gases?.thc?.[0])" colspan="2">{{ fmtGas(g1.gases?.thc?.[0]) }}</td>
                <td class="g1-val" colspan="2">{{ fmtGas(g1.gases?.thc?.[1]) }}</td>
                <td class="g1-val">{{ fmtGas(g1.gases?.thc?.[2]) }}</td>
                <td class="g1-val empty">—</td>
              </tr>
              <tr>
                <td class="g1-sub" colspan="2">分析意见</td>
                <td class="g1-opinion" colspan="6">{{ g1.opinion }}</td>
              </tr>
            </table>
            <p class="g1-foot-note">{{ g1.empty_note }}</p>
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

.toolbar { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; }
.nav { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.lbl { font-size: 12px; color: var(--fg-3); }
.date-pick { width: 160px; }
.jump { display: inline-flex; align-items: center; gap: 6px; }
.elig-select {
  min-width: 180px;
  padding: 6px 8px; border-radius: 6px;
  border: 1px solid var(--line-2); background: var(--bg-3); color: var(--fg);
  font-size: 12px;
}
.actions { display: flex; gap: 8px; }
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
}
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
.msg-arrow { margin: 0 4px; color: var(--fg-4); }
.msg-result {
  font-weight: 700;
  color: #fbbf24;
}
.tone-detect .msg-result { color: #5eead4; }
.tone-diag .msg-result { color: #f0c674; }
.tone-trend .msg-result { color: #7dd3fc; }
.tone-agent .msg-result { color: #c4b5fd; }
.tone-report .msg-result { color: #fda4af; }
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
.g1-preview.locked { opacity: 0.45; pointer-events: none; filter: grayscale(0.3); }
.g1-placeholder {
  padding: 28px; text-align: center; color: var(--fg-4); font-size: 12px;
  border: 1px dashed var(--line); border-radius: 8px;
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
.dec-s { font-size: 11px; color: var(--fg-4); line-height: 1.5; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.trial-list { margin: 6px 0 0; padding-left: 18px; font-size: 12px; color: var(--fg-2); line-height: 1.55; }
.decision-lock {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  background: rgba(20,28,36,0.72); color: var(--fg-3); font-size: 12px;
  border-radius: var(--r);
}

/* 表 G.1 */
.g1-sheet {
  background: #fff; color: #111;
  border: 2px solid #111;
  font-family: 'Songti SC', 'SimSun', 'Noto Serif SC', serif;
  font-size: 13px; line-height: 1.35;
}
.g1-sheet.compact { font-size: 10px; border-width: 1px; }
.g1-title {
  text-align: center; font-weight: 700; letter-spacing: 2px;
  padding: 8px; border-bottom: 1px solid #111;
}
.g1-sheet.compact .g1-title { font-size: 12px; letter-spacing: 1px; padding: 6px; }
.g1-meta {
  display: flex; justify-content: space-between; gap: 12px;
  padding: 6px 10px; border-bottom: 1px solid #111; font-size: 12px;
}
.g1-sheet.compact .g1-meta { font-size: 10px; padding: 4px 6px; }
.g1-meta-line {
  display: inline-block; min-width: 100px; border-bottom: 1px solid #111; height: 1em;
}
.g1-meta-no { display: inline-block; min-width: 90px; border-bottom: 1px solid #111; text-align: center; }
.g1-table { width: 100%; border-collapse: collapse; }
.g1-table td {
  border: 1px solid #111; padding: 4px 6px; vertical-align: middle;
}
.g1-lbl, .g1-sub, .g1-section {
  background: #f3f3f3; font-weight: 600; white-space: nowrap;
}
.g1-section { text-align: center; writing-mode: horizontal-tb; }
.g1-val.empty { color: #888; }
.g1-val.warn { color: #b45309; font-weight: 700; }
.g1-val.over { color: #b91c1c; font-weight: 700; }
.g1-opinion { font-size: 11px; line-height: 1.55; }
.g1-sheet.compact .g1-opinion { font-size: 10px; }
.g1-foot-note { margin: 8px 10px; font-size: 11px; color: #666; }

.modal {
  position: fixed; inset: 0; z-index: 90;
  display: flex; align-items: center; justify-content: center;
}
.modal-backdrop { position: absolute; inset: 0; background: rgba(0,0,0,0.55); }
.modal-dialog {
  position: relative;
  width: min(920px, calc(100vw - 32px));
  max-height: calc(100vh - 48px);
  overflow: hidden; display: flex; flex-direction: column;
  border-radius: var(--r-lg); border: 1px solid var(--line);
  background: var(--bg-2); box-shadow: 0 16px 48px rgba(0,0,0,0.45);
}
.modal-head {
  display: flex; justify-content: space-between; gap: 12px;
  padding: 14px 16px; border-bottom: 1px solid var(--line);
}
.modal-head h3 { margin: 0 0 4px; font-size: 15px; }
.modal-meta { font-size: 11px; color: var(--fg-4); }
.modal-x { border: none; background: transparent; color: var(--fg-3); font-size: 22px; cursor: pointer; }
.modal-body { padding: 14px 16px; overflow-y: auto; background: #1a222c; }
.modal-foot {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 12px 16px; border-top: 1px solid var(--line);
}

.toolbar :deep(.el-input__wrapper) {
  background: var(--bg-3) !important;
  box-shadow: 0 0 0 1px var(--line-2) inset !important;
}
.toolbar :deep(.el-input__inner) { color: var(--fg) !important; }
</style>

<style>
.el-date-table td.ag-alarm .el-date-table-cell__text {
  background: rgba(245, 85, 90, 0.28) !important; color: #fca5a5 !important; border-radius: 50%;
}
.el-date-table td.ag-w2 .el-date-table-cell__text {
  background: rgba(251, 146, 60, 0.25) !important; color: #fdba74 !important; border-radius: 50%;
}
.el-date-table td.ag-w1 .el-date-table-cell__text {
  box-shadow: inset 0 -2px 0 #fbbf24;
}
.el-date-table td.ag-pre .el-date-table-cell__text {
  box-shadow: inset 0 -2px 0 #67e8f9;
}
</style>
