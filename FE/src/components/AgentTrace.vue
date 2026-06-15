<template>
  <div class="agent-trace flex flex-col h-full">
    <!-- 顶部状态条(接真 /api/agent/run,LangChain ReAct 轨迹)-->
    <div class="trace-statusbar">
      <div class="flex items-center gap-2">
        <span class="text-xs font-bold text-gray-100">ReAct 推理</span>
        <span class="text-[10px] text-gray-500">{{ steps.length }} 步</span>
        <span v-if="totalDuration" class="text-[10px] text-gray-500 font-mono">· {{ totalDuration }}</span>
        <span class="status-chip" :class="runStatus">
          <iconify-icon :icon="statusIcon"></iconify-icon>
          {{ statusLabel }}
        </span>
      </div>
    </div>

    <!-- ReAct 5 步时间线 -->
    <div class="flex-1 overflow-y-auto pr-1" style="min-height: 0">
      <div class="trace-timeline">
        <div
          v-for="(s, i) in steps"
          :key="i"
          class="trace-item"
          :class="s.status"
        >
          <div class="trace-conn" v-if="i < steps.length - 1"></div>
          <div class="trace-dot">
            <iconify-icon :icon="stepIcon(s.status)" class="text-base"></iconify-icon>
          </div>
          <div class="trace-body">
            <div class="flex items-center justify-between cursor-pointer" @click="toggle(i)">
              <div class="flex items-center gap-2">
                <span class="step-idx">{{ i + 1 }}</span>
                <span class="text-xs font-bold text-gray-100 font-mono">{{ s.tool }}</span>
              </div>
              <div class="flex items-center gap-2">
                <span v-if="s.duration" class="text-[10px] text-gray-500 font-mono">{{ s.duration }}</span>
                <iconify-icon
                  class="text-gray-500 text-sm"
                  :icon="expanded[i] ? 'mdi:chevron-up' : 'mdi:chevron-down'"
                ></iconify-icon>
              </div>
            </div>
            <p class="text-[11px] text-gray-400 mt-0.5">{{ s.summary }}</p>

            <!-- ReAct 三要素(展开)-->
            <div v-show="expanded[i]" class="react-detail">
              <div v-if="s.thought" class="react-row">
                <span class="react-tag tag-thought">Thought</span>
                <span class="react-text">{{ s.thought }}</span>
              </div>
              <div v-if="s.action" class="react-row">
                <span class="react-tag tag-action">Action</span>
                <span class="react-text font-mono">{{ s.action }}</span>
              </div>
              <div v-if="s.observation" class="react-row">
                <span class="react-tag tag-obs">Observation</span>
                <span class="react-text font-mono">{{ s.observation }}</span>
              </div>
              <!-- 失败/降级原因高亮 -->
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
  // 整轮总耗时(ms);后端 /api/agent/run 顶层 duration_ms,优先用它
  durationMs: { type: Number, default: 0 },
});

const expanded = ref({});
function toggle(i) {
  expanded.value[i] = !expanded.value[i];
}

const totalDuration = computed(() => {
  // 优先用后端整轮真实耗时(durationMs);缺省时回退逐步 duration 累加(兼容)
  if (props.durationMs) return (props.durationMs / 1000).toFixed(1) + "s";
  const ms = props.steps.reduce((sum, s) => {
    const m = (s.duration || "").match(/([\d.]+)\s*s/);
    return sum + (m ? parseFloat(m[1]) : 0);
  }, 0);
  return ms ? ms.toFixed(1) + "s" : "";
});

const STATUS_META = {
  success: { label: "执行成功", icon: "mdi:check-circle" },
  fallback: { label: "降级为纯 Pipeline", icon: "mdi:backup-restore" },
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
.trace-statusbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  margin-bottom: 8px;
  background: rgba(31, 41, 55, 0.5);
  border: 1px solid rgba(75, 85, 99, 0.3);
  border-radius: 6px;
}
.status-chip {
  font-size: 10px;
  padding: 1px 8px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  border: 1px solid;
}
.status-chip.success { color: #6ee7b7; background: rgba(16, 185, 129, 0.15); border-color: rgba(16, 185, 129, 0.4); }
.status-chip.fallback { color: #fdba74; background: rgba(249, 115, 22, 0.15); border-color: rgba(249, 115, 22, 0.4); }
.status-chip.running { color: #67e8f9; background: rgba(6, 182, 212, 0.15); border-color: rgba(6, 182, 212, 0.4); }

.planning-pill {
  font-size: 10px;
  color: #d8b4fe;
  background: rgba(168, 85, 247, 0.15);
  border: 1px solid rgba(168, 85, 247, 0.4);
  padding: 2px 8px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  white-space: nowrap;
}

.trace-timeline { position: relative; padding: 2px 0; }
.trace-item { position: relative; display: flex; gap: 12px; padding-bottom: 14px; }
.trace-item:last-child { padding-bottom: 0; }
.trace-conn {
  position: absolute;
  left: 13px; top: 28px; bottom: -14px;
  width: 2px;
  background: rgba(75, 85, 99, 0.4);
}
.trace-dot {
  width: 28px; height: 28px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  border: 2px solid rgba(75, 85, 99, 0.4);
  background: rgba(31, 41, 55, 0.8);
  color: #9ca3af;
  z-index: 1;
}
.trace-item.success .trace-dot { border-color: #10b981; background: rgba(16, 185, 129, 0.15); color: #10b981; }
.trace-item.running .trace-dot { border-color: #06b6d4; background: rgba(6, 182, 212, 0.15); color: #06b6d4; animation: pulse 2s ease-in-out infinite; }
.trace-item.error .trace-dot { border-color: #ef4444; background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.trace-item.pending .trace-dot { border-color: rgba(75, 85, 99, 0.4); color: #6b7280; }

.trace-body {
  flex: 1;
  background: rgba(31, 41, 55, 0.5);
  border: 1px solid rgba(75, 85, 99, 0.35);
  border-radius: 6px;
  padding: 8px 10px;
}
.trace-item.success .trace-body { border-color: rgba(16, 185, 129, 0.25); }
.trace-item.error .trace-body { border-color: rgba(239, 68, 68, 0.3); background: rgba(239, 68, 68, 0.05); }
.step-idx {
  width: 18px; height: 18px;
  border-radius: 50%;
  background: rgba(168, 85, 247, 0.2);
  color: #d8b4fe;
  font-size: 10px; font-weight: 700;
  display: inline-flex; align-items: center; justify-content: center;
}

.react-detail {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed rgba(75, 85, 99, 0.4);
  display: flex; flex-direction: column; gap: 5px;
}
.react-row { display: flex; align-items: flex-start; gap: 8px; }
.react-tag {
  flex-shrink: 0;
  font-size: 9px;
  padding: 1px 6px;
  border-radius: 3px;
  border: 1px solid;
  font-weight: 600;
  min-width: 72px;
  text-align: center;
}
.tag-thought { background: rgba(6, 182, 212, 0.15); color: #67e8f9; border-color: rgba(6, 182, 212, 0.4); }
.tag-action { background: rgba(168, 85, 247, 0.15); color: #d8b4fe; border-color: rgba(168, 85, 247, 0.4); }
.tag-obs { background: rgba(249, 115, 22, 0.15); color: #fdba74; border-color: rgba(249, 115, 22, 0.4); }
.react-text { font-size: 11px; color: #d1d5db; line-height: 1.5; }
.react-error {
  display: flex; align-items: center; gap: 4px;
  font-size: 11px; color: #fca5a5;
  background: rgba(239, 68, 68, 0.1);
  border-radius: 4px; padding: 4px 8px;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 8px rgba(6, 182, 212, 0.3); }
  50% { box-shadow: 0 0 16px rgba(6, 182, 212, 0.6); }
}
</style>
