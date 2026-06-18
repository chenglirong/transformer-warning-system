<template>
  <div class="agent-trace flex flex-col h-full">
    <!-- ① 决策结论卡(主:第一眼最醒目,Agent 推出的预警结论)-->
    <div class="verdict-card" :class="runStatus">
      <div class="verdict-head">
        <span class="verdict-level" :class="'lv-' + (conclusion.levelKey || 'none')">
          {{ conclusion.level || "无预警" }}
        </span>
        <span class="verdict-status" :class="runStatus">
          <iconify-icon :icon="statusIcon"></iconify-icon>
          {{ statusLabel }}
        </span>
      </div>
      <div class="verdict-body">
        <div class="verdict-row">
          <span class="verdict-key">触发规则</span>
          <span class="verdict-val font-mono">{{ conclusion.ruleIds || "—" }}</span>
        </div>
        <div class="verdict-row">
          <span class="verdict-key">响应级别</span>
          <span class="verdict-val">{{ conclusion.response || "—" }}</span>
        </div>
      </div>
      <div class="verdict-foot">
        <span><iconify-icon icon="mdi:robot-outline"></iconify-icon> LangChain Agent · ReAct</span>
        <span>{{ steps.length }} 步推理<template v-if="totalDuration"> · ⏱ {{ totalDuration }}</template></span>
      </div>
      <!-- 降级时点明已回退规则引擎 -->
      <div v-if="runStatus === 'fallback'" class="verdict-fallback">
        <iconify-icon icon="mdi:backup-restore"></iconify-icon>
        Agent 推理未完成,已降级为纯规则引擎 Pipeline 得出上述结论
      </div>
    </div>

    <!-- ② 推理过程(并重:可折叠的 ReAct 时间线)-->
    <div class="reason-head" @click="showSteps = !showSteps">
      <span class="flex items-center gap-1.5">
        <iconify-icon icon="mdi:sitemap-outline"></iconify-icon>
        推理过程(Thought → Action → Observation)
      </span>
      <iconify-icon :icon="showSteps ? 'mdi:chevron-up' : 'mdi:chevron-down'"></iconify-icon>
    </div>

    <div v-show="showSteps" class="flex-1 overflow-y-auto pr-1" style="min-height: 0">
      <div class="trace-timeline">
        <div v-for="(s, i) in steps" :key="i" class="trace-item" :class="s.status">
          <div class="trace-conn" v-if="i < steps.length - 1"></div>
          <div class="trace-dot">
            <iconify-icon :icon="stepIcon(s.status)" class="text-base"></iconify-icon>
          </div>
          <div class="trace-body">
            <div class="flex items-center justify-between cursor-pointer" @click="toggle(i)">
              <div class="flex items-center gap-2">
                <span class="step-idx">{{ i + 1 }}</span>
                <span class="text-xs font-bold text-gray-100">{{ s.tool }}</span>
              </div>
              <iconify-icon
                class="text-gray-500 text-sm"
                :icon="expanded[i] ? 'mdi:chevron-up' : 'mdi:chevron-down'"
              ></iconify-icon>
            </div>
            <p class="text-[11px] text-gray-400 mt-0.5">{{ s.summary }}</p>

            <!-- ReAct 三要素(展开;配色区分思考/行动/观察)-->
            <div v-show="expanded[i]" class="react-detail">
              <div v-if="s.thought" class="react-row">
                <span class="react-tag tag-thought">💭 Thought</span>
                <span class="react-text">{{ s.thought }}</span>
              </div>
              <div v-if="s.action" class="react-row">
                <span class="react-tag tag-action">⚡ Action</span>
                <span class="react-text font-mono">{{ s.action }}</span>
              </div>
              <div v-if="s.observation" class="react-row">
                <span class="react-tag tag-obs">👁 Observation</span>
                <span class="react-text font-mono">{{ s.observation }}</span>
              </div>
              <div v-if="s.status === 'error'" class="react-error">
                <iconify-icon icon="mdi:alert"></iconify-icon>
                {{ s.errorReason || "该步骤执行失败" }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";

const props = defineProps({
  // 每步:{ tool, summary, status:'success'|'running'|'error'|'pending',
  //        thought, action, observation, errorReason }(后端不含逐步耗时)
  steps: { type: Array, default: () => [] },
  // 整轮状态:success | fallback | running
  runStatus: { type: String, default: "success" },
  // 整轮总耗时(ms);后端 /api/agent/run 顶层 duration_ms
  durationMs: { type: Number, default: 0 },
  // 决策结论(主卡):{ level, levelKey, ruleIds, response } —— 由父级从工单传入
  conclusion: { type: Object, default: () => ({}) },
});

const expanded = ref({});
const showSteps = ref(true);          // 推理过程默认展开,可折叠
function toggle(i) {
  expanded.value[i] = !expanded.value[i];
}

const totalDuration = computed(() => {
  if (props.durationMs) return (props.durationMs / 1000).toFixed(1) + "s";
  return "";
});

const STATUS_META = {
  success: { label: "执行成功", icon: "mdi:check-circle" },
  fallback: { label: "已降级", icon: "mdi:backup-restore" },
  running: { label: "执行中", icon: "mdi:loading" },
};
const statusLabel = computed(() => (STATUS_META[props.runStatus] || STATUS_META.success).label);
const statusIcon = computed(() => (STATUS_META[props.runStatus] || STATUS_META.success).icon);

function stepIcon(status) {
  return {
    success: "mdi:check",
    running: "mdi:loading",
    error: "mdi:close",
    pending: "mdi:dots-horizontal",
  }[status] || "mdi:circle-small";
}
</script>

<style scoped>
/* ① 决策结论卡 */
.verdict-card {
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 10px;
  background: linear-gradient(135deg, rgba(31, 41, 55, 0.9), rgba(17, 24, 39, 0.7));
  border: 1px solid rgba(75, 85, 99, 0.4);
  border-left: 3px solid #6b7280;
}
.verdict-card.success { border-left-color: #10b981; }
.verdict-card.fallback { border-left-color: #f97316; }
.verdict-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px;
}
.verdict-level {
  font-size: 18px; font-weight: 800; letter-spacing: 1px;
  padding: 2px 12px; border-radius: 6px;
}
.lv-red { color: #fca5a5; background: rgba(239, 68, 68, 0.18); }
.lv-orange { color: #fdba74; background: rgba(249, 115, 22, 0.18); }
.lv-yellow { color: #fde047; background: rgba(234, 179, 8, 0.18); }
.lv-blue { color: #93c5fd; background: rgba(59, 130, 246, 0.18); }
.lv-none { color: #9ca3af; background: rgba(107, 114, 128, 0.15); font-size: 14px; }
.verdict-status {
  font-size: 11px; padding: 2px 10px; border-radius: 12px;
  display: inline-flex; align-items: center; gap: 4px; border: 1px solid;
}
.verdict-status.success { color: #6ee7b7; background: rgba(16, 185, 129, 0.15); border-color: rgba(16, 185, 129, 0.4); }
.verdict-status.fallback { color: #fdba74; background: rgba(249, 115, 22, 0.15); border-color: rgba(249, 115, 22, 0.4); }
.verdict-status.running { color: #67e8f9; background: rgba(6, 182, 212, 0.15); border-color: rgba(6, 182, 212, 0.4); }
.verdict-body { display: flex; flex-direction: column; gap: 4px; }
.verdict-row { display: flex; align-items: center; gap: 10px; }
.verdict-key {
  font-size: 10px; color: #9ca3af; min-width: 56px;
}
.verdict-val { font-size: 13px; color: #e5e7eb; font-weight: 600; }
.verdict-foot {
  display: flex; align-items: center; justify-content: space-between;
  margin-top: 8px; padding-top: 7px;
  border-top: 1px solid rgba(75, 85, 99, 0.3);
  font-size: 10px; color: #a78bfa;
}
.verdict-foot span { display: inline-flex; align-items: center; gap: 4px; }
.verdict-fallback {
  display: flex; align-items: center; gap: 5px;
  margin-top: 8px; font-size: 10px; color: #fdba74;
  background: rgba(249, 115, 22, 0.1); border-radius: 5px; padding: 5px 8px;
}

/* ② 推理过程折叠头 */
.reason-head {
  display: flex; align-items: center; justify-content: space-between;
  cursor: pointer; padding: 5px 4px; margin-bottom: 4px;
  font-size: 11px; font-weight: 700; color: #67e8f9;
  border-bottom: 1px solid rgba(75, 85, 99, 0.25);
}

/* 时间线(沿用,微调)*/
.trace-timeline { position: relative; padding: 4px 0; }
.trace-item { position: relative; display: flex; gap: 12px; padding-bottom: 12px; }
.trace-item:last-child { padding-bottom: 0; }
.trace-conn { position: absolute; left: 13px; top: 28px; bottom: -12px; width: 2px; background: rgba(75, 85, 99, 0.4); }
.trace-dot {
  width: 28px; height: 28px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  border: 2px solid rgba(75, 85, 99, 0.4); background: rgba(31, 41, 55, 0.8);
  color: #9ca3af; z-index: 1;
}
.trace-item.success .trace-dot { border-color: #10b981; background: rgba(16, 185, 129, 0.15); color: #10b981; }
.trace-item.error .trace-dot { border-color: #ef4444; background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.trace-body { flex: 1; background: rgba(31, 41, 55, 0.5); border: 1px solid rgba(75, 85, 99, 0.35); border-radius: 6px; padding: 8px 10px; }
.trace-item.success .trace-body { border-color: rgba(16, 185, 129, 0.25); }
.trace-item.error .trace-body { border-color: rgba(239, 68, 68, 0.3); background: rgba(239, 68, 68, 0.05); }
.step-idx {
  width: 18px; height: 18px; border-radius: 50%;
  background: rgba(168, 85, 247, 0.2); color: #d8b4fe;
  font-size: 10px; font-weight: 700;
  display: inline-flex; align-items: center; justify-content: center;
}

.react-detail {
  margin-top: 8px; padding-top: 8px;
  border-top: 1px dashed rgba(75, 85, 99, 0.4);
  display: flex; flex-direction: column; gap: 6px;
}
.react-row { display: flex; align-items: flex-start; gap: 8px; }
.react-tag {
  flex-shrink: 0; font-size: 9px; padding: 2px 6px; border-radius: 3px;
  border: 1px solid; font-weight: 600; min-width: 88px; text-align: center;
}
.tag-thought { background: rgba(6, 182, 212, 0.15); color: #67e8f9; border-color: rgba(6, 182, 212, 0.4); }
.tag-action { background: rgba(168, 85, 247, 0.15); color: #d8b4fe; border-color: rgba(168, 85, 247, 0.4); }
.tag-obs { background: rgba(249, 115, 22, 0.15); color: #fdba74; border-color: rgba(249, 115, 22, 0.4); }
.react-text { font-size: 11px; color: #d1d5db; line-height: 1.5; word-break: break-all; }
.react-error {
  display: flex; align-items: center; gap: 4px;
  font-size: 11px; color: #fca5a5;
  background: rgba(239, 68, 68, 0.1); border-radius: 4px; padding: 4px 8px;
}
</style>
