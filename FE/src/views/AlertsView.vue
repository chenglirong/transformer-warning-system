<template>
  <div class="h-screen flex flex-col">
    <AppHeader
      title="预 警 工 单 工 作 台"
      icon="mdi:clipboard-list"
      subtitle="4 级分级 · 规则引擎触发 · 点单追溯 Agent 推理"
    />

    <!-- 顶部:预警态势概览(四级可筛选)-->
    <section class="px-3 pt-3 grid grid-cols-5 gap-3">
      <div class="kpi-mini" :class="filter === 'all' ? 'active' : ''" @click="setFilter('all')">
        <p class="text-[11px] text-gray-400">触发总数</p>
        <p class="text-2xl font-bold text-cyan-300">{{ totalAlerts }}<span class="text-xs ml-1">天</span></p>
      </div>
      <div class="kpi-mini border-red" :class="filter === 'red' ? 'active' : ''" @click="setFilter('red')">
        <p class="text-[11px] text-gray-400">🔴 红色 · 立即响应</p>
        <p class="text-2xl font-bold text-red-400">{{ dist.red }}</p>
      </div>
      <div class="kpi-mini border-org" :class="filter === 'orange' ? 'active' : ''" @click="setFilter('orange')">
        <p class="text-[11px] text-gray-400">🟠 橙色 · 24h</p>
        <p class="text-2xl font-bold text-orange-400">{{ dist.orange }}</p>
      </div>
      <div class="kpi-mini border-yel" :class="filter === 'yellow' ? 'active' : ''" @click="setFilter('yellow')">
        <p class="text-[11px] text-gray-400">🟡 黄色 · 加强监测</p>
        <p class="text-2xl font-bold text-yellow-400">{{ dist.yellow }}</p>
      </div>
      <div class="kpi-mini border-blu" :class="filter === 'blue' ? 'active' : ''" @click="setFilter('blue')">
        <p class="text-[11px] text-gray-400">🔵 蓝色 · 日常关注</p>
        <p class="text-2xl font-bold text-blue-400">{{ dist.blue }}</p>
      </div>
    </section>

    <main class="flex-1 grid grid-cols-12 gap-3 p-3 overflow-hidden" style="min-height: 0">
      <!-- LEFT col-5:工单列表(全量 + 分页 + 筛选 + 排序 + 搜索)-->
      <div class="col-span-5 glass rounded-lg p-3 flex flex-col overflow-hidden">
        <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between">
          <span class="flex items-center gap-2">
            <iconify-icon icon="mdi:format-list-bulleted"></iconify-icon>
            告警工单（{{ filtered.length }} 条）
          </span>
        </h3>

        <!-- 工具条:搜索 + 规则类型 + 排序 -->
        <div class="flex items-center gap-2 mb-2">
          <input
            v-model="search"
            class="toolbar-input flex-1"
            placeholder="搜索日期 / 规则编号(如 2025-03 / S-01)"
          />
          <select v-model="ruleTypeFilter" class="toolbar-input">
            <option value="all">全部规则</option>
            <option value="hard">硬规则</option>
            <option value="soft">软规则</option>
            <option value="combo">组合规则</option>
          </select>
          <button class="toolbar-btn" @click="toggleSort">
            <iconify-icon :icon="sortBy === 'time' ? 'mdi:clock-outline' : 'mdi:fire'"></iconify-icon>
            {{ sortBy === 'time' ? '按时间' : '按紧急度' }}
          </button>
        </div>

        <div class="flex-1 overflow-y-auto space-y-2 pr-1" style="min-height: 0">
          <div
            v-for="t in paged"
            :key="t.id"
            class="ticket-card"
            :class="[t.borderClass, selected && selected.id === t.id ? 'selected' : '']"
            @click="selected = t"
          >
            <div class="flex items-center justify-between mb-1">
              <div class="flex items-center gap-2">
                <span class="text-[10px] px-1.5 py-0.5 rounded font-bold" :class="t.tag">{{ t.level }}</span>
                <span class="text-[10px] text-cyan-300 font-mono">{{ t.id }}</span>
                <span
                  v-if="agentDates.has(t.date)"
                  class="agent-traceable"
                  title="该工单有 Agent 预跑推理轨迹,可点单追溯"
                >
                  <iconify-icon icon="mdi:robot-outline"></iconify-icon>
                  可追溯
                </span>
              </div>
              <span class="text-[10px] text-gray-500">{{ t.date }}</span>
            </div>
            <p class="text-[12px] text-gray-100 leading-snug">{{ t.title }}</p>
            <div class="flex items-center justify-between mt-1.5">
              <span class="text-[10px] text-gray-500">{{ t.ruleTypeLabel }}</span>
              <span class="text-[10px] text-gray-500 font-mono">{{ t.ruleIds }}</span>
            </div>
          </div>
          <p v-if="!filtered.length" class="text-[12px] text-gray-500 text-center mt-4">无匹配工单</p>
        </div>

        <!-- 分页器 -->
        <div v-if="totalPages > 1" class="flex items-center justify-between mt-2 text-[11px] text-gray-400">
          <button class="page-btn" :disabled="page === 1" @click="page--">上一页</button>
          <span>{{ page }} / {{ totalPages }}（每页 {{ pageSize }} 条）</span>
          <button class="page-btn" :disabled="page === totalPages" @click="page++">下一页</button>
        </div>
      </div>

      <!-- RIGHT col-7:详情 + Agent 追溯 -->
      <div class="col-span-7 flex flex-col gap-3 overflow-hidden">
        <!-- 上半:预警信息 -->
        <div v-if="selected" class="glass rounded-lg p-3" style="flex: 0 0 auto">
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-3">
              <span class="text-[10px] px-2 py-0.5 rounded font-bold" :class="selected.tag">{{ selected.level }}</span>
              <span class="text-base font-bold text-gray-100">{{ selected.title }}</span>
            </div>
            <div class="flex items-center gap-2 text-[10px] text-gray-500">
              <span class="font-mono">{{ selected.id }}</span><span>·</span><span>{{ selected.date }}</span>
            </div>
          </div>
          <div class="grid grid-cols-3 gap-2">
            <div class="info-cell">
              <p class="text-[10px] text-gray-400">触发规则编号</p>
              <p class="text-xs font-mono text-cyan-300 mt-0.5">{{ selected.ruleIds }}</p>
            </div>
            <div class="info-cell">
              <p class="text-[10px] text-gray-400">规则类型</p>
              <p class="text-[11px] text-gray-200 mt-0.5">{{ selected.ruleTypeLabel }}</p>
            </div>
            <div class="info-cell">
              <p class="text-[10px] text-gray-400">响应级别</p>
              <p class="text-[11px] text-gray-200 mt-0.5">{{ selected.response }}</p>
            </div>
          </div>
        </div>

        <!-- 中:Agent 推理追溯(接真 /api/agent/run,LangChain ReAct)-->
        <div class="glass rounded-lg p-3 overflow-hidden flex flex-col" style="flex: 1">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center gap-2">
            <iconify-icon icon="mdi:robot-outline"></iconify-icon>
            Agent 推理追溯（该预警如何被推导）
          </h3>
          <div class="flex-1 overflow-hidden" style="min-height: 0">
            <AgentTrace v-if="selected && agentReady" :steps="agentSteps" :run-status="agentRunStatus" :duration-ms="agentDurationMs" />
            <p v-else-if="selected && agentLoading" class="text-xs text-gray-500 p-2">加载 Agent 轨迹…</p>
            <p v-else-if="selected" class="text-xs text-gray-500 p-2 leading-relaxed">
              该工单未预跑 Agent 轨迹。<br />
              Agent 预跑覆盖各等级代表性工单(脚本 scripts/run_agent_demo.py 离线落盘);
              其余工单可后续按需补跑。
            </p>
          </div>
        </div>

        <!-- 下:AI 预警通知(LLM 生成,接真 Agent Final Answer)-->
        <div v-if="selected && agentReady" class="glass rounded-lg p-3 overflow-hidden flex flex-col" style="flex: 0.7">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center gap-2">
            <iconify-icon icon="mdi:bullhorn-outline"></iconify-icon>
            AI 预警通知（LLM 生成）
          </h3>
          <pre class="notice-block flex-1">{{ noticeText }}</pre>
        </div>
      </div>
    </main>

    <AppFooter />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import AppHeader from "@/components/AppHeader.vue";
import AppFooter from "@/components/AppFooter.vue";
import AgentTrace from "@/components/AgentTrace.vue";
import { getWarningBacktest, getAgentRun, getAgentDates } from "@/service/api";

// ============ 真值兜底(防 Demo 断网)============
// 来源:GET /api/warning/backtest(scripts/backtest.py 落盘的全量告警)。
const FALLBACK = {
  level_distribution: { red: 80, orange: 13, yellow: 135, blue: 0 },
  n_alerts: 0,
  alerts: [],
};
const data = ref(FALLBACK);

// 已预跑 Agent 轨迹的工单日期(给「可追溯」工单卡片打标;预跑仅覆盖代表性工单)
const agentDates = ref(new Set());

onMounted(async () => {
  try {
    const r = await getWarningBacktest();
    if (r?.alerts) data.value = r;
  } catch (e) {
    console.warn("[AlertsView] 回测接口拉取失败,使用兜底常量", e);
  }
  try {
    const d = await getAgentDates(1);   // 单设备方案 transformer_id=1
    agentDates.value = new Set(d?.dates || []);
  } catch (e) {
    console.warn("[AlertsView] Agent 预跑日期拉取失败", e);
  }
});

const dist = computed(() => data.value.level_distribution);
const totalAlerts = computed(() => Object.values(dist.value).reduce((a, b) => a + b, 0));

// 等级元信息
const LEVEL_META = {
  red: { label: "🔴 红色", tag: "tag-red", border: "border-red-500/50", rank: 4, response: "立即响应" },
  orange: { label: "🟠 橙色", tag: "tag-org", border: "border-orange-500/50", rank: 3, response: "24 小时内处理" },
  yellow: { label: "🟡 黄色", tag: "tag-yel", border: "border-yellow-500/50", rank: 2, response: "加强监测" },
  blue: { label: "🔵 蓝色", tag: "tag-blu", border: "border-blue-500/50", rank: 1, response: "日常关注" },
};
const RULE_TYPE_LABEL = { hard: "硬规则(已超标)", soft: "软规则(预测/趋势)", combo: "组合规则" };
function ruleTypeLabelOf(types) {
  return (types || []).map((t) => RULE_TYPE_LABEL[t] || t).join(" + ");
}

// 全量工单映射(无故障类型/无运维建议/无置信度;不显误报——运维当下不知真值)
const allTickets = computed(() =>
  (data.value.alerts || []).map((a, i) => {
    const meta = LEVEL_META[a.level] || LEVEL_META.blue;
    return {
      id: "WO-" + String(i + 1).padStart(3, "0"),
      date: a.date,
      levelKey: a.level,
      level: meta.label,
      tag: meta.tag,
      borderClass: meta.border,
      rank: meta.rank,
      response: meta.response,
      ruleIds: a.rule_ids.join(", "),
      ruleTypes: a.rule_types || [],
      ruleTypeLabel: ruleTypeLabelOf(a.rule_types),
      title: `触发 ${a.rule_ids.join("、")}`,
    };
  })
);

// 筛选 + 搜索 + 排序
const filter = ref("all");
const ruleTypeFilter = ref("all");
const search = ref("");
const sortBy = ref("time");
const page = ref(1);
const pageSize = 20;

function setFilter(f) {
  filter.value = f;
  page.value = 1;
}
function toggleSort() {
  sortBy.value = sortBy.value === "time" ? "urgency" : "time";
  page.value = 1;
}
watch([ruleTypeFilter, search], () => (page.value = 1));

const filtered = computed(() => {
  let list = allTickets.value;
  if (filter.value !== "all") list = list.filter((t) => t.levelKey === filter.value);
  if (ruleTypeFilter.value !== "all")
    list = list.filter((t) => t.ruleTypes.includes(ruleTypeFilter.value));
  const q = search.value.trim().toLowerCase();
  if (q) list = list.filter((t) => t.date.includes(q) || t.ruleIds.toLowerCase().includes(q));
  list = [...list];
  if (sortBy.value === "time") list.sort((a, b) => b.date.localeCompare(a.date));
  else list.sort((a, b) => b.rank - a.rank || b.date.localeCompare(a.date));
  return list;
});

const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / pageSize)));
const paged = computed(() => filtered.value.slice((page.value - 1) * pageSize, page.value * pageSize));

const selected = ref(null);
watch(filtered, (list) => {
  if ((!selected.value || !list.includes(selected.value)) && list.length) selected.value = list[0];
  else if (!list.length) selected.value = null;
});

// ============ Agent ReAct 轨迹(接真 /api/agent/run,模块6)============
// 选中工单时按工单日期拉该工单的 Agent 预跑轨迹(scripts/run_agent_demo.py 离线
// 落盘,D-027 在线轻量)。预跑只覆盖代表性工单,未覆盖的工单据实显「未预跑」占位
// (不杜撰,承 D-023)。守边界:轨迹/通知由后端 Prompt+黑名单双校验守住。
const agentSteps = ref([]);
const agentRunStatus = ref("success");
const noticeText = ref("");
const agentReady = ref(false);          // 该工单是否有预跑轨迹
const agentLoading = ref(false);
const agentDurationMs = ref(0);         // 整轮真实耗时(后端 duration_ms)

async function loadAgentTrace(t) {
  agentReady.value = false;
  agentSteps.value = [];
  noticeText.value = "";
  agentDurationMs.value = 0;
  if (!t) return;
  agentLoading.value = true;
  try {
    const r = await getAgentRun(1, t.date);   // 单设备方案 transformer_id=1
    agentSteps.value = r.steps || [];
    agentRunStatus.value = r.status || "success";
    noticeText.value = r.notice || "";
    agentDurationMs.value = r.duration_ms || 0;
    agentReady.value = (r.steps || []).length > 0;
  } catch (e) {
    // 404 = 该工单未预跑 Agent(预跑仅覆盖代表性工单),据实占位
    agentReady.value = false;
  } finally {
    agentLoading.value = false;
  }
}
watch(selected, (t) => loadAgentTrace(t));
</script>

<style scoped>
.kpi-mini {
  background: rgba(17, 24, 39, 0.7);
  border: 1px solid rgba(75, 85, 99, 0.4);
  border-radius: 6px;
  padding: 8px 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.kpi-mini:hover { border-color: rgba(6, 182, 212, 0.4); background: rgba(6, 182, 212, 0.05); }
.kpi-mini.active { border-color: rgba(6, 182, 212, 0.6); background: rgba(6, 182, 212, 0.08); box-shadow: inset 0 0 16px rgba(6, 182, 212, 0.1); }
.kpi-mini.border-red.active { border-color: rgba(239, 68, 68, 0.6); background: rgba(239, 68, 68, 0.08); }
.kpi-mini.border-org.active { border-color: rgba(249, 115, 22, 0.6); background: rgba(249, 115, 22, 0.08); }
.kpi-mini.border-yel.active { border-color: rgba(234, 179, 8, 0.6); background: rgba(234, 179, 8, 0.08); }
.kpi-mini.border-blu.active { border-color: rgba(59, 130, 246, 0.6); background: rgba(59, 130, 246, 0.08); }

.toolbar-input {
  background: rgba(17, 24, 39, 0.8);
  border: 1px solid rgba(75, 85, 99, 0.4);
  border-radius: 5px;
  padding: 4px 8px;
  font-size: 11px;
  color: #e5e7eb;
  outline: none;
}
.toolbar-input:focus { border-color: rgba(6, 182, 212, 0.5); }
.toolbar-btn {
  background: rgba(17, 24, 39, 0.8);
  border: 1px solid rgba(75, 85, 99, 0.4);
  border-radius: 5px;
  padding: 4px 8px;
  font-size: 11px;
  color: #9ca3af;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  white-space: nowrap;
}
.toolbar-btn:hover { border-color: rgba(6, 182, 212, 0.5); color: #67e8f9; }

.ticket-card {
  background: rgba(31, 41, 55, 0.5);
  border: 1px solid rgba(75, 85, 99, 0.3);
  border-left-width: 3px;
  border-radius: 5px;
  padding: 8px 10px;
  cursor: pointer;
  transition: all 0.2s;
}
.ticket-card:hover { background: rgba(59, 130, 246, 0.08); }
.ticket-card.selected { background: rgba(6, 182, 212, 0.1); border-color: rgba(6, 182, 212, 0.5); box-shadow: inset 0 0 14px rgba(6, 182, 212, 0.08); }

.info-cell {
  background: rgba(31, 41, 55, 0.5);
  border: 1px solid rgba(75, 85, 99, 0.3);
  border-radius: 4px;
  padding: 6px 8px;
}

.page-btn {
  background: rgba(17, 24, 39, 0.8);
  border: 1px solid rgba(75, 85, 99, 0.4);
  border-radius: 4px;
  padding: 3px 10px;
  color: #9ca3af;
  cursor: pointer;
}
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.page-btn:not(:disabled):hover { border-color: rgba(6, 182, 212, 0.5); color: #67e8f9; }

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
.agent-traceable {
  font-size: 9px;
  color: #d8b4fe;
  background: rgba(168, 85, 247, 0.15);
  border: 1px solid rgba(168, 85, 247, 0.35);
  padding: 1px 6px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  white-space: nowrap;
}
.notice-block {
  background: #0f172a;
  border: 1px solid rgba(6, 182, 212, 0.3);
  border-radius: 4px;
  padding: 10px;
  color: #d1d5db;
  white-space: pre-wrap;
  font-family: "JetBrains Mono", "Consolas", monospace;
  font-size: 11px;
  line-height: 1.6;
  overflow-y: auto;
  margin: 0;
}
</style>
