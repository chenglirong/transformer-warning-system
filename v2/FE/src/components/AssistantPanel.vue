<script setup>
import { ref, watch, nextTick } from 'vue'
import StdCite from '@/components/StdCite.vue'
import { chatAssistant, getAssistantSuggestions, syncAssistant } from '@/service/assistantApi'

const props = defineProps({
  visible: { type: Boolean, default: false },
  selectedDate: { type: String, default: '' },
  /** Agent 主区当前分析结果（按钮跑完分析后传入） */
  agentResult: { type: Object, default: null },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'analysis-result', 'selected-day'])

const messages = ref([])
const input = ref('')
const sending = ref(false)
const sessionId = ref(null)
const suggestions = ref([])
const listRef = ref(null)
const booted = ref(false)
const lastSyncedKey = ref('')
const lastPushedAnalysisKey = ref('')
const lastSyncMeta = ref({ key: '', reply: '', citeIds: [] })
const expandedSteps = ref(new Set())

function toggleSteps(idx) {
  const next = new Set(expandedSteps.value)
  if (next.has(idx)) next.delete(idx)
  else next.add(idx)
  expandedSteps.value = next
}

function isStepsExpanded(idx) {
  return expandedSteps.value.has(idx)
}

function resultSyncKey(result) {
  if (!result?.date) return ''
  const steps = result.steps || []
  const lastLog = steps.map((s) => s.log || '').join('|')
  return `${result.date}:${result.grade || ''}:${lastLog.slice(0, 120)}`
}

function nowTs() {
  const t = new Date()
  const pad = (n) => (n < 10 ? `0${n}` : `${n}`)
  return `${pad(t.getHours())}:${pad(t.getMinutes())}:${pad(t.getSeconds())}`
}

function scrollBottom() {
  nextTick(() => {
    const el = listRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

async function loadSuggestions() {
  try {
    const res = await getAssistantSuggestions()
    suggestions.value = res?.questions || []
  } catch {
    suggestions.value = [
      '帮我分析当前日期',
      '涨势预警什么意思？',
      '三比值法怎么读？',
    ]
  }
}

function pushUser(text) {
  messages.value.push({
    role: 'user',
    type: 'text',
    content: { text },
    timestamp: nowTs(),
  })
}

function pushAssistant(payload) {
  messages.value.push({
    role: 'assistant',
    type: payload.type || 'text',
    content: {
      text: payload.reply || '',
      cite_ids: payload.cite_ids || [],
      result: payload.result || null,
      mode: payload.mode || null,
    },
    timestamp: nowTs(),
  })
}

function upsertAnalysisBubble(result, reply, citeIds = [], { mode = null, showSteps = false } = {}) {
  const key = resultSyncKey(result)
  if (!key || !reply) return
  let idx = -1
  for (let i = messages.value.length - 1; i >= 0; i -= 1) {
    const m = messages.value[i]
    if (m.type === 'analysis_result' && m.content.syncKey === key) {
      idx = i
      break
    }
  }
  const msg = {
    role: 'assistant',
    type: 'analysis_result',
    content: {
      text: reply,
      cite_ids: citeIds,
      result: showSteps ? result : null,
      showSteps,
      syncKey: key,
      mode,
    },
    timestamp: nowTs(),
  }
  if (idx >= 0) messages.value[idx] = msg
  else messages.value.push(msg)
  lastPushedAnalysisKey.value = key
}

function boot() {
  if (booted.value) return
  booted.value = true
  pushAssistant({
    reply: '你好，我是 DGA 分析助手。可问「今天的气体怎么样？」或指定日期运行分析；解释以 Agent 七步规则为准。',
    type: 'guidance',
  })
  // 有主区结果时交给 sync 填推荐，避免默认 chips 异步覆盖
  if (!props.agentResult) loadSuggestions()
}

async function syncFromAgent(result, { pushBubble = false } = {}) {
  if (!result?.date) return null
  const key = resultSyncKey(result)
  if (!key) return null

  const needApi = key !== lastSyncedKey.value
  const needBubble = pushBubble && key !== lastPushedAnalysisKey.value
  if (!needApi && !needBubble) return null

  if (needApi) {
    try {
      const data = await syncAssistant({
        sessionId: sessionId.value,
        day: result.date,
        result,
      })
      sessionId.value = data?.session_id || sessionId.value
      if (data?.suggestions?.length) {
        suggestions.value = data.suggestions
      }
      lastSyncedKey.value = key
      lastSyncMeta.value = {
        key,
        reply: data?.reply || '',
        citeIds: data?.cite_ids || [],
      }
      if (needBubble && data?.reply) {
        upsertAnalysisBubble(result, data.reply, data.cite_ids || [], {
          mode: data.mode,
          showSteps: false,
        })
        scrollBottom()
      }
      return data
    } catch {
      return null
    }
  }

  if (needBubble) {
    const meta = lastSyncMeta.value.key === key ? lastSyncMeta.value : null
    const reply = meta?.reply
      || `已同步 ${result.date} 的主区分析结果，可直接追问档位、趋势或判型。`
    upsertAnalysisBubble(result, reply, meta?.citeIds || [], { showSteps: false })
    scrollBottom()
  }
  return null
}

async function sendMessage(text) {
  const msg = (text || input.value || '').trim()
  if (!msg || sending.value || props.disabled) return
  input.value = ''
  pushUser(msg)
  scrollBottom()
  sending.value = true
  try {
    const data = await chatAssistant(msg, {
      sessionId: sessionId.value,
      selectedDate: props.selectedDate || null,
    })
    sessionId.value = data?.session_id || sessionId.value
    if (data?.suggestions?.length) {
      suggestions.value = data.suggestions
    }
    if (data?.result) {
      lastSyncedKey.value = resultSyncKey(data.result)
      lastSyncMeta.value = {
        key: lastSyncedKey.value,
        reply: data?.reply || '',
        citeIds: data?.cite_ids || [],
      }
      upsertAnalysisBubble(
        data.result,
        data?.reply || '（无回复）',
        data?.cite_ids || [],
        { mode: data?.mode, showSteps: true },
      )
      emit('analysis-result', data.result)
    } else {
      pushAssistant({
        reply: data?.reply || '（无回复）',
        cite_ids: data?.cite_ids || [],
        mode: data?.mode,
        type: 'explanation',
      })
    }
    if (data?.selected_day) {
      emit('selected-day', data.selected_day)
    }
  } catch (e) {
    pushAssistant({
      reply: e?.message || '请求失败，请稍后重试。',
      type: 'guidance',
    })
  } finally {
    sending.value = false
    scrollBottom()
  }
}

function onSuggestion(q) {
  let text = q
  if (q.includes('当前日期') && props.selectedDate) {
    text = `帮我分析 ${props.selectedDate}`
  }
  sendMessage(text)
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

watch(
  () => props.visible,
  (v) => {
    if (!v) return
    boot()
    if (props.agentResult) {
      syncFromAgent(props.agentResult, { pushBubble: true })
    }
  },
)

watch(
  () => props.agentResult,
  async (r) => {
    if (!r) return
    await syncFromAgent(r, { pushBubble: props.visible })
  },
  { deep: true },
)
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="assistant-overlay" @click.self="emit('close')">
      <aside class="assistant-panel" role="dialog" aria-label="分析助手">
        <header class="panel-head">
          <div>
            <h3>分析助手</h3>
          </div>
          <button type="button" class="btn-close" aria-label="关闭" @click="emit('close')">×</button>
        </header>

        <div v-if="suggestions.length" class="chips">
          <button
            v-for="(q, i) in suggestions"
            :key="i"
            type="button"
            class="chip"
            :disabled="sending || disabled"
            @click="onSuggestion(q)"
          >
            {{ q }}
          </button>
        </div>

        <div ref="listRef" class="msg-list">
          <div
            v-for="(m, i) in messages"
            :key="i"
            class="msg"
            :class="m.role"
          >
            <div class="bubble" :class="{ 'analysis-bubble': m.type === 'analysis_result' }">
              <template v-if="m.type === 'analysis_result'">
                <template v-if="m.content.showSteps && m.content.result">
                  <button
                    type="button"
                    class="steps-toggle"
                    @click="toggleSteps(i)"
                  >
                    <span class="chevron" :class="{ open: isStepsExpanded(i) }">›</span>
                    <span>分析过程</span>
                    <span class="steps-count">{{ m.content.result.steps?.length || 0 }} 步</span>
                  </button>
                  <div
                    v-show="isStepsExpanded(i) && m.content.result.steps?.length"
                    class="step-summary"
                  >
                    <div
                      v-for="s in m.content.result.steps"
                      :key="s.id"
                      class="step-row"
                      :class="{ 'step-skipped': s.skipped }"
                    >
                      <span class="step-label">{{ s.label }}</span>
                      <span class="step-log">{{ s.log || (s.skipped ? '已跳过' : '—') }}</span>
                    </div>
                  </div>
                </template>
                <p v-if="m.content.text" class="text" :class="{ 'text-after-steps': m.content.showSteps }">{{ m.content.text }}</p>
                <div v-if="m.content.cite_ids?.length" class="cites">
                  <StdCite
                    v-for="cid in m.content.cite_ids"
                    :key="cid"
                    inline
                    :ref-id="cid"
                  />
                </div>
                <div v-if="m.content.showSteps" class="result-hint">主区时间线已同步</div>
              </template>
              <template v-else>
                <p class="text">{{ m.content.text }}</p>
                <div v-if="m.content.cite_ids?.length" class="cites">
                  <StdCite
                    v-for="cid in m.content.cite_ids"
                    :key="cid"
                    inline
                    :ref-id="cid"
                  />
                </div>
              </template>
            </div>
            <span class="ts">{{ m.timestamp }}</span>
          </div>
          <div v-if="sending" class="msg assistant">
            <div class="bubble typing">正在回复…</div>
          </div>
        </div>

        <footer class="panel-foot">
          <textarea
            v-model="input"
            class="input"
            rows="2"
            placeholder="例如：今天的气体怎么样？"
            :disabled="sending || disabled"
            @keydown="onKeydown"
          />
          <button
            type="button"
            class="btn-send"
            :disabled="sending || disabled || !input.trim()"
            @click="sendMessage()"
          >
            发送
          </button>
        </footer>
      </aside>
    </div>
  </Teleport>
</template>

<style scoped>
.assistant-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  justify-content: flex-end;
}
.assistant-panel {
  width: min(640px, 100vw);
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-2, #1a2332);
  border-left: 1px solid var(--line, rgba(160, 174, 192, 0.2));
  box-shadow: -8px 0 32px rgba(0, 0, 0, 0.35);
}
.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 16px 12px;
  border-bottom: 1px solid var(--line, rgba(160, 174, 192, 0.15));
}
.panel-head h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--fg-1, #e8edf4);
}
.btn-close {
  border: none;
  background: transparent;
  color: var(--fg-3);
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
  padding: 0 4px;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--line, rgba(160, 174, 192, 0.1));
}
.chip {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--teal-line, rgba(45, 212, 191, 0.35));
  background: rgba(45, 212, 191, 0.08);
  color: var(--teal-2, #5eead4);
  cursor: pointer;
}
.chip:disabled { opacity: 0.5; cursor: not-allowed; }
.msg-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}
.msg {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 92%;
}
.msg.user { align-self: flex-end; align-items: flex-end; }
.msg.assistant { align-self: flex-start; align-items: flex-start; }
.bubble {
  padding: 10px 12px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.55;
}
.msg.user .bubble {
  background: rgba(59, 130, 246, 0.25);
  border: 1px solid rgba(96, 165, 250, 0.35);
  color: var(--fg-1);
}
.msg.assistant .bubble {
  background: var(--bg-3, #243044);
  border: 1px solid var(--line);
  color: var(--fg-2, #c5d0de);
}
.bubble.typing { color: var(--fg-4); font-style: italic; }
.bubble.analysis-bubble {
  font-size: 11px;
  line-height: 1.45;
}
.bubble.analysis-bubble .text {
  font-size: 11px;
}
.bubble.analysis-bubble .cites :deep(.std-cite) {
  font-size: 10px;
}
.text { margin: 0; white-space: pre-wrap; word-break: break-word; }
.text-after-steps {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(160, 174, 192, 0.1);
}
.cites {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}
.steps-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0;
  margin: 0 0 4px;
  border: none;
  background: transparent;
  color: var(--fg-4);
  font-size: 11px;
  cursor: pointer;
  text-align: left;
}
.steps-toggle:hover {
  color: var(--fg-3);
}
.chevron {
  display: inline-block;
  font-size: 12px;
  line-height: 1;
  transition: transform 0.15s ease;
  color: var(--fg-4);
}
.chevron.open {
  transform: rotate(90deg);
}
.steps-count {
  color: var(--fg-4);
  font-size: 10px;
}
.step-summary {
  margin: 0 0 6px;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.step-row {
  display: grid;
  grid-template-columns: 4.2em 1fr;
  gap: 4px;
  font-size: 11px;
  line-height: 1.4;
}
.step-label {
  color: var(--fg-4);
  flex-shrink: 0;
}
.step-log {
  color: var(--fg-3);
  word-break: break-word;
}
.step-skipped .step-label,
.step-skipped .step-log {
  color: var(--fg-4);
  opacity: 0.55;
}
.result-hint {
  margin-top: 6px;
  font-size: 10px;
  color: var(--teal-2);
}
.ts {
  font-size: 10px;
  color: var(--fg-4);
  font-family: 'JetBrains Mono', monospace;
}
.panel-foot {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid var(--line);
  align-items: flex-end;
}
.input {
  flex: 1;
  resize: none;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: var(--bg-3);
  color: var(--fg-1);
  padding: 8px 10px;
  font-size: 13px;
  font-family: inherit;
}
.btn-send {
  flex-shrink: 0;
  padding: 8px 16px;
  border-radius: 8px;
  border: none;
  background: var(--teal, #14b8a6);
  color: #042f2e;
  font-weight: 700;
  font-size: 13px;
  cursor: pointer;
}
.btn-send:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
