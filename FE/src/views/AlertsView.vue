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

        <!-- 工具条:搜索 + 规则类型 + 排序 + 规则库 -->
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
          <button class="toolbar-btn" @click="showRules = true" title="查看预警规则库全貌">
            <iconify-icon icon="mdi:book-open-variant"></iconify-icon>
            规则库
          </button>
        </div>

        <!-- 工单表格 -->
        <div class="flex-1 overflow-y-auto pr-1" style="min-height: 0">
          <table class="wo-table">
            <thead>
              <tr>
                <th class="w-14">等级</th>
                <th class="w-16">工单号</th>
                <th>日期</th>
                <th>触发规则</th>
                <th class="w-10 text-center" title="有 Agent 推理轨迹">🤖</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="t in paged"
                :key="t.id"
                class="wo-row"
                :class="selected && selected.id === t.id ? 'selected' : ''"
                @click="selected = t"
              >
                <td><span class="lv-pill" :class="t.tag">{{ t.levelShort }}</span></td>
                <td class="font-mono text-cyan-300 text-[10px]">{{ t.id }}</td>
                <td class="text-gray-400 text-[10px]">{{ t.date }}</td>
                <td class="font-mono text-gray-200 text-[10px]">{{ t.ruleIds }}</td>
                <td class="text-center">
                  <iconify-icon
                    v-if="agentDates.has(t.date)"
                    icon="mdi:robot-outline"
                    class="text-purple-300"
                    title="可点单追溯 Agent 推理"
                  ></iconify-icon>
                </td>
              </tr>
            </tbody>
          </table>
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
          <!-- 触发明细:逐条展示带确切数值的 message(实测值/注意值/预测值/涨幅)-->
          <div v-if="selected.messages && selected.messages.length" class="mt-2 flex flex-col gap-1">
            <p class="text-[10px] text-gray-400">触发明细</p>
            <div
              v-for="m in selected.messages"
              :key="m.rule_id"
              class="trigger-msg"
              :class="'tmsg-' + m.level"
            >
              <span class="font-mono text-[10px] opacity-70">{{ m.rule_id }}</span>
              <span>{{ m.message }}</span>
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
            <AgentTrace v-if="selected && agentReady" :steps="agentSteps" :run-status="agentRunStatus" :duration-ms="agentDurationMs" :conclusion="agentConclusion" />
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

    <!-- 规则库总览(右侧抽屉)-->
    <el-drawer
      v-model="showRules"
      title="预警规则库"
      direction="rtl"
      size="520px"
      class="rules-drawer"
    >
      <p class="rules-intro">
        规则引擎共 <b>{{ rulesData.n_rules || 0 }}</b> 条,分四类。综合等级取所有触发规则的最高级(红 &gt; 橙 &gt; 黄 &gt; 蓝)。规则只判定「哪个气体 / 什么条件 / 什么等级」,不输出故障类型。
      </p>
      <div v-for="g in rulesData.groups" :key="g.type" class="rule-group">
        <div class="rule-group-head">
          <span class="rule-group-label">{{ g.label }}</span>
          <span class="rule-group-count">{{ g.rules.length }} 条</span>
          <span class="rule-group-desc">{{ g.desc }}</span>
        </div>
        <div
          v-for="r in g.rules"
          :key="r.id"
          class="rule-row"
          :class="'lvl-' + r.level.split('/')[0]"
        >
          <div class="rule-row-head">
            <span class="rule-id">{{ r.id }}</span>
            <span class="rule-lv">{{ levelText(r.level) }}</span>
          </div>
          <p class="rule-cond">{{ r.condition }}</p>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import AppHeader from "@/components/AppHeader.vue";
import AppFooter from "@/components/AppFooter.vue";
import AgentTrace from "@/components/AgentTrace.vue";
import { getWarningBacktest, getAgentRun, getAgentDates, getWarningRules } from "@/service/api";

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

// 规则库抽屉
const showRules = ref(false);
const rulesData = ref({ groups: [], n_rules: 0 });

// 等级 key → 「中文-响应紧迫」标签(规则库抽屉显示用)。软规则 level 为 'red/orange'
const LEVEL_TEXT = {
  red: "红色-紧急",
  orange: "橙色-重要",
  yellow: "黄色-一般",
  blue: "蓝色-提示",
};
function levelText(level) {
  return (level || "")
    .split("/")
    .map((k) => LEVEL_TEXT[k] || k)
    .join(" / ");
}

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
  try {
    rulesData.value = await getWarningRules();
  } catch (e) {
    console.warn("[AlertsView] 规则库拉取失败", e);
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
      levelShort: meta.label.replace(/^\S+\s*/, ""),   // 去 emoji,表格等级列用「红/橙/黄/蓝」
      tag: meta.tag,
      borderClass: meta.border,
      rank: meta.rank,
      response: meta.response,
      ruleIds: a.rule_ids.join(", "),
      ruleTypes: a.rule_types || [],
      ruleTypeLabel: ruleTypeLabelOf(a.rule_types),
      title: `触发 ${a.rule_ids.join("、")}`,
      messages: a.messages || [],   // 触发明细(含确切数值),详情面板逐条展示
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

// Agent 决策结论(传给 AgentTrace 结论卡;取选中工单的权威等级/规则/响应)
const agentConclusion = computed(() => {
  const t = selected.value;
  if (!t) return {};
  return {
    level: t.levelShort,
    levelKey: t.levelKey,
    ruleIds: t.ruleIds,
    response: t.response,
  };
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
/* 工单表格 */
.wo-table { width: 100%; border-collapse: collapse; font-size: 11px; }
.wo-table thead th {
  position: sticky; top: 0; z-index: 1;
  background: rgba(17, 24, 39, 0.95);
  color: #9ca3af; font-size: 10px; font-weight: 600;
  text-align: left; padding: 6px 8px;
  border-bottom: 1px solid rgba(75, 85, 99, 0.4);
}
.wo-table .w-14 { width: 48px; }
.wo-table .w-16 { width: 64px; }
.wo-table .w-10 { width: 36px; }
.wo-row { cursor: pointer; transition: background 0.15s; border-bottom: 1px solid rgba(75, 85, 99, 0.18); }
.wo-row td { padding: 6px 8px; }
.wo-row:hover { background: rgba(59, 130, 246, 0.08); }
.wo-row.selected { background: rgba(6, 182, 212, 0.12); box-shadow: inset 2px 0 0 #06b6d4; }
.lv-pill { font-size: 10px; font-weight: 700; padding: 1px 7px; border-radius: 4px; white-space: nowrap; }

/* 规则库抽屉 */
/* el-drawer 深色主题覆盖:干掉默认灰 header / 配深色 body */
:deep(.rules-drawer) {
  background: #0f172a;
}
:deep(.rules-drawer .el-drawer__header) {
  margin-bottom: 0;
  padding: 18px 22px;
  background: transparent;
  border-bottom: 1px solid rgba(103, 232, 249, 0.25);
  color: #67e8f9;
  font-size: 18px;
  font-weight: 800;
}
:deep(.rules-drawer .el-drawer__title) {
  color: #67e8f9; font-size: 18px; font-weight: 800;
}
:deep(.rules-drawer .el-drawer__close-btn) { color: #94a3b8; }
:deep(.rules-drawer .el-drawer__close-btn:hover) { color: #67e8f9; }
:deep(.rules-drawer .el-drawer__body) {
  padding: 20px 22px;
  background: #0f172a;
}

.rules-intro {
  font-size: 12px; line-height: 1.7; color: #94a3b8;
  margin-bottom: 22px;
}
.rules-intro b { color: #67e8f9; font-size: 14px; }
.rule-group { margin-bottom: 26px; }
.rule-group-head {
  display: flex; align-items: center; gap: 10px; margin-bottom: 12px;
}
.rule-group-label { font-size: 17px; font-weight: 800; color: #e5e7eb; }
.rule-group-count { font-size: 12px; color: #67e8f9; font-weight: 700; }
.rule-group-desc { font-size: 12px; color: #94a3b8; }

/* 每条规则:左侧等级色条 + 颜色身份,无灰底无灰线,靠间距分隔 */
.rule-row {
  padding: 12px 0 12px 16px;
  border-left: 4px solid;
  margin-bottom: 14px;
}
.rule-row-head {
  display: flex; align-items: center; gap: 12px; margin-bottom: 7px;
}
.rule-id {
  font-size: 17px; font-weight: 800;
  font-family: monospace; letter-spacing: 1px;
}
.rule-lv {
  font-size: 13px; font-weight: 700;
  padding: 3px 12px; border-radius: 20px;
}
.rule-cond { font-size: 14px; color: #f1f5f9; line-height: 1.55; font-weight: 600; }
.rule-msg { font-size: 13px; color: #94a3b8; line-height: 1.55; margin-top: 4px; }
.trigger-msg { font-size: 12px; color: #cbd5e1; line-height: 1.5; padding: 4px 8px;
  border-radius: 4px; background: rgba(148,163,184,0.08); display: flex; gap: 6px;
  align-items: baseline; border-left: 2px solid #64748b; }
.trigger-msg.tmsg-red { border-left-color: #f87171; }
.trigger-msg.tmsg-orange { border-left-color: #fb923c; }
.trigger-msg.tmsg-yellow { border-left-color: #facc15; }
.trigger-msg.tmsg-blue { border-left-color: #60a5fa; }

/* 等级配色:色条 / 编号 / 徽章统一用该等级色 */
.rule-row.lvl-red { border-left-color: #ef4444; }
.rule-row.lvl-red .rule-id { color: #f87171; }
.rule-row.lvl-red .rule-lv { color: #fecaca; background: rgba(239, 68, 68, 0.22); }
.rule-row.lvl-orange { border-left-color: #f97316; }
.rule-row.lvl-orange .rule-id { color: #fb923c; }
.rule-row.lvl-orange .rule-lv { color: #fed7aa; background: rgba(249, 115, 22, 0.22); }
.rule-row.lvl-yellow { border-left-color: #eab308; }
.rule-row.lvl-yellow .rule-id { color: #facc15; }
.rule-row.lvl-yellow .rule-lv { color: #fef08a; background: rgba(234, 179, 8, 0.22); }
.rule-row.lvl-blue { border-left-color: #3b82f6; }
.rule-row.lvl-blue .rule-id { color: #60a5fa; }
.rule-row.lvl-blue .rule-lv { color: #bfdbfe; background: rgba(59, 130, 246, 0.22); }

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
