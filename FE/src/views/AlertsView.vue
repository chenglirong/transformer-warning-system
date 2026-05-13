<template>
  <div class="h-screen flex flex-col">
    <AppHeader
      title="预 警 工 单 与  A g e n t  推 理"
      icon="mdi:clipboard-list"
      subtitle="4 级分级 · 规则原文 · ReAct 推理追溯"
    />

    <!-- 顶部 KPI -->
    <section class="px-3 pt-3 grid grid-cols-5 gap-3">
      <div
        class="kpi-mini"
        :class="filter === 'all' ? 'active' : ''"
        @click="filter = 'all'"
      >
        <p class="text-[11px] text-gray-400">全部工单</p>
        <p class="text-2xl font-bold text-cyan-300">
          10<span class="text-xs ml-1">条</span>
        </p>
      </div>
      <div
        class="kpi-mini border-red"
        :class="filter === '红' ? 'active' : ''"
        @click="filter = '红'"
      >
        <p class="text-[11px] text-gray-400">🔴 红色</p>
        <p class="text-2xl font-bold text-red-400">1</p>
      </div>
      <div
        class="kpi-mini border-org"
        :class="filter === '橙' ? 'active' : ''"
        @click="filter = '橙'"
      >
        <p class="text-[11px] text-gray-400">🟠 橙色</p>
        <p class="text-2xl font-bold text-orange-400">3</p>
      </div>
      <div
        class="kpi-mini border-yel"
        :class="filter === '黄' ? 'active' : ''"
        @click="filter = '黄'"
      >
        <p class="text-[11px] text-gray-400">🟡 黄色</p>
        <p class="text-2xl font-bold text-yellow-400">4</p>
      </div>
      <div
        class="kpi-mini border-blu"
        :class="filter === '蓝' ? 'active' : ''"
        @click="filter = '蓝'"
      >
        <p class="text-[11px] text-gray-400">🔵 蓝色</p>
        <p class="text-2xl font-bold text-blue-400">2</p>
      </div>
    </section>

    <main
      class="flex-1 grid grid-cols-12 gap-3 p-3 overflow-hidden"
      style="min-height: 0"
    >
      <!-- LEFT col-5: 工单列表 -->
      <div
        class="col-span-5 glass rounded-lg p-3 flex flex-col overflow-hidden"
      >
        <h3
          class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between"
        >
          <span class="flex items-center gap-2">
            <iconify-icon icon="mdi:format-list-bulleted"></iconify-icon>
            工单列表（{{ filteredTickets.length }} / {{ tickets.length }}）
          </span>
          <span class="text-[10px] text-gray-500">点击查看 Agent 推理详情</span>
        </h3>
        <div
          class="flex-1 overflow-y-auto space-y-2 pr-1"
          style="min-height: 0"
        >
          <div
            v-for="t in filteredTickets"
            :key="t.id"
            class="ticket-card"
            :class="[t.borderClass, selected.id === t.id ? 'selected' : '']"
            @click="selected = t"
          >
            <div class="flex items-center justify-between mb-1">
              <div class="flex items-center gap-2">
                <span
                  class="text-[10px] px-1.5 py-0.5 rounded font-bold"
                  :class="t.tag"
                >
                  {{ t.level }}
                </span>
                <span class="text-[10px] text-cyan-300 font-mono">{{
                  t.id
                }}</span>
              </div>
              <span class="text-[10px] text-gray-500">{{ t.time }}</span>
            </div>
            <p class="text-[12px] text-gray-100 leading-snug">{{ t.title }}</p>
            <div class="flex items-center justify-between mt-1.5">
              <span class="text-[10px] text-gray-500">{{ t.ruleType }}</span>
              <span
                class="text-[10px] px-1.5 py-0.5 rounded"
                :class="t.statusTag"
              >
                {{ t.status }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- RIGHT col-7: 选中工单详情 + Agent 推理 -->
      <div class="col-span-7 flex flex-col gap-3 overflow-hidden">
        <!-- 工单详情 + 规则 -->
        <div
          class="glass rounded-lg p-3 overflow-hidden"
          style="flex: 0 0 auto"
        >
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-3">
              <span
                class="text-[10px] px-2 py-0.5 rounded font-bold"
                :class="selected.tag"
              >
                {{ selected.level }}
              </span>
              <span class="text-base font-bold text-gray-100">{{
                selected.title
              }}</span>
            </div>
            <div class="flex items-center gap-2 text-[10px] text-gray-500">
              <span class="font-mono">{{ selected.id }}</span>
              <span>·</span>
              <span>{{ selected.time }}</span>
            </div>
          </div>
          <div class="grid grid-cols-3 gap-2">
            <div class="info-cell">
              <p class="text-[10px] text-gray-400">触发规则</p>
              <p class="text-xs text-gray-200 mt-0.5">{{ selected.ruleId }}</p>
              <p class="text-[10px] text-gray-500">{{ selected.ruleType }}</p>
            </div>
            <div class="info-cell">
              <p class="text-[10px] text-gray-400">规则表达式</p>
              <p class="text-[11px] font-mono text-cyan-300 mt-0.5">
                {{ selected.ruleExpr }}
              </p>
            </div>
            <div class="info-cell">
              <p class="text-[10px] text-gray-400">处置建议</p>
              <p class="text-[11px] text-gray-200 mt-0.5">
                {{ selected.advice }}
              </p>
            </div>
          </div>
        </div>

        <!-- Agent ReAct 推理追踪 -->
        <div
          class="glass rounded-lg p-3 overflow-hidden flex flex-col"
          style="flex: 1.2"
        >
          <h3
            class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between"
          >
            <span class="flex items-center gap-2">
              <iconify-icon icon="mdi:robot-outline"></iconify-icon>
              Agent ReAct 推理追踪（5 步）
            </span>
            <span class="text-[10px] text-purple-300 flex items-center gap-1">
              <iconify-icon icon="mdi:brain"></iconify-icon> 通义千问 qwen-turbo
            </span>
          </h3>
          <div
            class="flex-1 overflow-y-auto space-y-2 pr-1"
            style="min-height: 0"
          >
            <div
              v-for="(s, i) in selected.agent"
              :key="i"
              class="react-step"
              :class="s.status"
            >
              <div class="flex items-center gap-2 mb-1">
                <span class="step-num">{{ i + 1 }}</span>
                <span class="text-xs font-bold text-gray-100">{{
                  s.title
                }}</span>
                <span class="text-[10px] text-gray-500 ml-auto">{{
                  s.time
                }}</span>
                <iconify-icon
                  class="text-base"
                  :class="s.iconClass"
                  :icon="s.icon"
                ></iconify-icon>
              </div>
              <div class="ml-8 space-y-1">
                <div class="trace-row">
                  <span class="trace-tag tag-thought">Thought</span>
                  <span class="trace-text">{{ s.thought }}</span>
                </div>
                <div class="trace-row">
                  <span class="trace-tag tag-action">Action</span>
                  <span class="trace-text font-mono">{{ s.action }}</span>
                </div>
                <div class="trace-row">
                  <span class="trace-tag tag-observation">Observation</span>
                  <span class="trace-text font-mono">{{ s.observation }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Final Answer 通知 -->
        <div
          class="glass rounded-lg p-3 overflow-hidden"
          style="flex: 0 0 auto"
        >
          <h3
            class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between"
          >
            <span class="flex items-center gap-2">
              <iconify-icon icon="mdi:bullhorn"></iconify-icon>
              LLM Final Answer · 预警通知
            </span>
            <span class="text-[10px] text-green-400 flex items-center gap-1">
              <span class="live-dot"></span> 已生成 · 已入库
            </span>
          </h3>
          <pre class="notification-block">{{ selected.notification }}</pre>
        </div>
      </div>
    </main>

    <AppFooter />
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import AppHeader from "@/components/AppHeader.vue";
import AppFooter from "@/components/AppFooter.vue";

const filter = ref("all");

const buildAgent = (extras = {}) => [
  {
    title: "get_today_data 获取最新数据",
    time: "09:00:01",
    status: "success",
    icon: "mdi:check-circle",
    iconClass: "text-green-400",
    thought: "需要获取最新 DGA + 工况数据用于后续分析。",
    action: "get_today_data()",
    observation:
      extras.obs1 ||
      "{H₂:42.5, CH₄:58.2, C₂H₂:3.24, C₂H₄:45.1, 油温:59, 负载:1.05}",
  },
  {
    title: "detect_anomaly 异常检测",
    time: "09:00:03",
    status: "success",
    icon: "mdi:check-circle",
    iconClass: "text-green-400",
    thought: "调用 3 方法（阈值/三比值/孤立森林）检测当前是否存在异常信号。",
    action: "detect_anomaly(data=...)",
    observation:
      extras.obs2 ||
      "{threshold: 异常, iec_ratio: 异常(021低温过热), forest: 异常}",
  },
  {
    title: "lstm_predict 预测 1-3 天",
    time: "09:00:06",
    status: "success",
    icon: "mdi:check-circle",
    iconClass: "text-green-400",
    thought: "已检测异常，需要预测未来 1-3 天趋势判断恶化情况。",
    action: "lstm_predict(window=30, horizon=3)",
    observation:
      extras.obs3 || "C₂H₂: D+1=3.42, D+2=3.68, D+3=4.05 (接近阈值5)",
  },
  {
    title: "check_warning 规则判级",
    time: "09:00:09",
    status: "success",
    icon: "mdi:check-circle",
    iconClass: "text-green-400",
    thought: "检测+预测均显示异常，调用规则引擎确定预警等级。",
    action: "check_warning(detection=..., prediction=...)",
    observation:
      extras.obs4 ||
      "{level: '红色', rule_id: ['R002','R005'], reason: '1-3天必超标'}",
  },
  {
    title: "LLM 生成预警通知文本",
    time: "09:00:14",
    status: "success",
    icon: "mdi:check-circle",
    iconClass: "text-cyan-400",
    thought: "所有工具调用完成，按 Prompt 模板格式生成 Final Answer 并入库。",
    action: "Final Answer · 通知模板生成",
    observation: extras.obs5 || "通知文本已生成 → 写入 warning 表 → 推送前端",
  },
];

const tickets = [
  {
    id: "WO-107",
    level: "🔴 红色",
    tag: "tag-red",
    borderClass: "border-red-500/50",
    time: "10:42",
    title: "C₂H₂ 预测 D+3 达 4.05 ppm，逼近阈值 5 ppm",
    ruleId: "R002 + R005",
    ruleType: "软规则 + 规则诊断",
    ruleExpr: "lstm_predict(C₂H₂, 3) > 阈值 × 0.8",
    advice: "立即停运，开展油质检测，排查内部故障",
    status: "待处置",
    statusTag: "tag-red",
    agent: buildAgent(),
    notification: `🚨 【红色预警】#2 主变

📊 当前状态：
   C₂H₂ = 3.24 ppm（阈值 5 ppm）
   三比值法判定：低温过热 (<300℃)
   3 方法检测一致：异常 (3/3)

🔮 预测趋势（LSTM 滚动预测）：
   D+1: 3.42 ppm
   D+2: 3.68 ppm
   D+3: 4.05 ppm（已逼近阈值，置信度 92%）

⚖️ 触发规则：
   R002 软规则（LSTM 预测超阈）
   R005 三比值法（编码 021）

🤖 LLM 复核：建议立即停运排查，置信度 92%`,
  },
  {
    id: "WO-106",
    level: "🟠 橙色",
    tag: "tag-org",
    borderClass: "border-orange-500/50",
    time: "10:15",
    title: "C₂H₄ 72h 上升 23%，1-3 天内可能超标",
    ruleId: "R003",
    ruleType: "软规则（趋势）",
    ruleExpr: "rate(C₂H₄, 72h) > 20%",
    advice: "加强监测，每日取样 1 次，结合油温综合分析",
    status: "处置中",
    statusTag: "tag-org",
    agent: buildAgent({
      obs2: "{threshold: 正常, iec_ratio: 关注, forest: 异常}",
      obs3: "C₂H₄: D+1=46.2, D+2=47.8, D+3=49.5",
      obs4: "{level: '橙色', rule_id: ['R003'], reason: '产气速率超阈'}",
    }),
    notification: `🟠 【橙色预警】#2 主变

📊 当前状态：
   C₂H₄ = 45.1 ppm（72h 上升 23%）
   产气速率：23% / 72h（阈值 20%）

🔮 预测趋势（LSTM）：
   D+1: 46.2 ppm
   D+2: 47.8 ppm
   D+3: 49.5 ppm

⚖️ 触发规则：R003 软规则（产气速率）

🤖 LLM 复核：趋势异常，建议加强监测`,
  },
  {
    id: "WO-105",
    level: "🟠 橙色",
    tag: "tag-org",
    borderClass: "border-orange-500/50",
    time: "09:58",
    title: "顶层油温 84℃ + 负载 1.05 倍，组合规则触发",
    ruleId: "R004",
    ruleType: "组合规则",
    ruleExpr: "油温 > 80 AND 负载 > 1.0",
    advice: "调整负载分配，降低过载电流，监测绕组温度",
    status: "处置中",
    statusTag: "tag-org",
    agent: buildAgent({
      obs1: "{油温:84, 负载:1.05, 环温:38, C₂H₂:0.68}",
      obs2: "{threshold: 正常, iec_ratio: 正常, forest: 正常 — DGA 无异常}",
      obs3: "DGA 7 气体均预测稳定",
      obs4: "{level: '橙色', rule_id: ['R004'], reason: '油温×负载组合规则'}",
    }),
    notification: `🟠 【橙色预警】#5 主变

📊 当前状态：
   顶层油温 = 84℃（阈值 95℃）
   负载电流 = 1.05 倍额定（阈值 1.1 倍）

🔮 预测趋势：DGA 暂稳定，但油温 × 负载组合需关注

⚖️ 触发规则：R004 组合规则

🤖 LLM 复核：调整负载分配可有效缓解`,
  },
  {
    id: "WO-104",
    level: "🟠 橙色",
    tag: "tag-org",
    borderClass: "border-orange-500/50",
    time: "09:30",
    title: "三比值法判定 → 低温过热 (<300℃)",
    ruleId: "R005",
    ruleType: "规则诊断",
    ruleExpr: "三比值编码 ∈ {001, 021, 022}",
    advice: "增加取样频次，结合油温综合分析",
    status: "处置中",
    statusTag: "tag-org",
    agent: buildAgent({
      obs2: "三比值编码 021 → 低温过热 (<300℃)",
      obs4: "{level: '橙色', rule_id: ['R005']}",
    }),
    notification: `🟠 【橙色预警】#3 主变

📊 当前状态：
   三比值法编码：021
   故障类型：低温过热 (<300℃)

⚖️ 触发规则：R005 规则诊断

🤖 LLM 复核：建议增加取样频次`,
  },
  {
    id: "WO-103",
    level: "🟡 黄色",
    tag: "tag-yel",
    borderClass: "border-yellow-500/50",
    time: "08:50",
    title: "H₂ 产气速率 8.2 ppm/72h，趋势异常",
    ruleId: "R003",
    ruleType: "软规则（趋势）",
    ruleExpr: "rate(H₂, 72h) > 5",
    advice: "加强监测，每日记录数据",
    status: "跟踪",
    statusTag: "tag-org",
    agent: buildAgent(),
    notification: `🟡 【黄色预警】H₂ 产气速率异常`,
  },
  {
    id: "WO-102",
    level: "🟡 黄色",
    tag: "tag-yel",
    borderClass: "border-yellow-500/50",
    time: "07:22",
    title: "负载电流 1.05 倍额定（长期）",
    ruleId: "R006",
    ruleType: "硬规则（工况）",
    ruleExpr: "负载 > 1.0 倍 持续 24h",
    advice: "调整负载分配",
    status: "跟踪",
    statusTag: "tag-org",
    agent: buildAgent(),
    notification: `🟡 【黄色预警】负载持续偏高`,
  },
  {
    id: "WO-101",
    level: "🟡 黄色",
    tag: "tag-yel",
    borderClass: "border-yellow-500/50",
    time: "06:45",
    title: "C₂H₆ 7 日上升 27%",
    ruleId: "R003",
    ruleType: "软规则（趋势）",
    ruleExpr: "rate(C₂H₆, 7d) > 25%",
    advice: "加强监测",
    status: "已闭环",
    statusTag: "tag-grn",
    agent: buildAgent(),
    notification: `🟡 【黄色预警】C₂H₆ 7 日上升`,
  },
  {
    id: "WO-100",
    level: "🟡 黄色",
    tag: "tag-yel",
    borderClass: "border-yellow-500/50",
    time: "05:30",
    title: "总烃 7 日 ↑ 18%",
    ruleId: "R003",
    ruleType: "软规则（趋势）",
    ruleExpr: "rate(总烃, 7d) > 15%",
    advice: "加强监测",
    status: "已闭环",
    statusTag: "tag-grn",
    agent: buildAgent(),
    notification: `🟡 【黄色预警】总烃 7 日上升`,
  },
  {
    id: "WO-099",
    level: "🔵 蓝色",
    tag: "tag-blu",
    borderClass: "border-blue-500/50",
    time: "04:10",
    title: "环境温度 38℃ 接近 40℃ 阈值",
    ruleId: "R007",
    ruleType: "硬规则（工况）",
    ruleExpr: "环温 > 35 AND 环温 < 40",
    advice: "日常关注",
    status: "跟踪",
    statusTag: "tag-gry",
    agent: buildAgent(),
    notification: `🔵 【蓝色提示】环境温度接近阈值`,
  },
  {
    id: "WO-098",
    level: "🔵 蓝色",
    tag: "tag-blu",
    borderClass: "border-blue-500/50",
    time: "02:30",
    title: "CO 轻微波动 +5%",
    ruleId: "R003",
    ruleType: "软规则（趋势）",
    ruleExpr: "rate(CO, 24h) > 3%",
    advice: "日常关注",
    status: "跟踪",
    statusTag: "tag-gry",
    agent: buildAgent(),
    notification: `🔵 【蓝色提示】CO 轻微波动`,
  },
];

const filteredTickets = computed(() =>
  filter.value === "all"
    ? tickets
    : tickets.filter((t) => t.level.includes(filter.value)),
);

const selected = ref(tickets[0]);
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
.kpi-mini:hover {
  border-color: rgba(6, 182, 212, 0.4);
  background: rgba(6, 182, 212, 0.05);
}
.kpi-mini.active {
  border-color: rgba(6, 182, 212, 0.6);
  background: rgba(6, 182, 212, 0.08);
  box-shadow: inset 0 0 16px rgba(6, 182, 212, 0.1);
}
.kpi-mini.border-red.active {
  border-color: rgba(239, 68, 68, 0.6);
  background: rgba(239, 68, 68, 0.08);
}
.kpi-mini.border-org.active {
  border-color: rgba(249, 115, 22, 0.6);
  background: rgba(249, 115, 22, 0.08);
}
.kpi-mini.border-yel.active {
  border-color: rgba(234, 179, 8, 0.6);
  background: rgba(234, 179, 8, 0.08);
}
.kpi-mini.border-blu.active {
  border-color: rgba(59, 130, 246, 0.6);
  background: rgba(59, 130, 246, 0.08);
}

.ticket-card {
  background: rgba(31, 41, 55, 0.5);
  border: 1px solid rgba(75, 85, 99, 0.3);
  border-left-width: 3px;
  border-radius: 5px;
  padding: 8px 10px;
  cursor: pointer;
  transition: all 0.2s;
}
.ticket-card:hover {
  background: rgba(59, 130, 246, 0.08);
}
.ticket-card.selected {
  background: rgba(6, 182, 212, 0.1);
  border-color: rgba(6, 182, 212, 0.5);
  box-shadow: inset 0 0 14px rgba(6, 182, 212, 0.08);
}

.info-cell {
  background: rgba(31, 41, 55, 0.5);
  border: 1px solid rgba(75, 85, 99, 0.3);
  border-radius: 4px;
  padding: 6px 8px;
}

.react-step {
  background: rgba(31, 41, 55, 0.5);
  border-left: 3px solid rgba(16, 185, 129, 0.5);
  border-radius: 4px;
  padding: 8px 10px;
}
.react-step.success {
  border-left-color: #10b981;
}
.step-num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(16, 185, 129, 0.2);
  color: #6ee7b7;
  font-weight: 700;
  font-size: 11px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(16, 185, 129, 0.4);
  flex-shrink: 0;
}
.trace-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 2px 0;
}
.trace-tag {
  flex-shrink: 0;
  font-size: 9px;
  padding: 1px 6px;
  border-radius: 3px;
  border: 1px solid;
  font-weight: 600;
  min-width: 76px;
  text-align: center;
}
.tag-thought {
  background: rgba(6, 182, 212, 0.15);
  color: #67e8f9;
  border-color: rgba(6, 182, 212, 0.4);
}
.tag-action {
  background: rgba(168, 85, 247, 0.15);
  color: #d8b4fe;
  border-color: rgba(168, 85, 247, 0.4);
}
.tag-observation {
  background: rgba(249, 115, 22, 0.15);
  color: #fdba74;
  border-color: rgba(249, 115, 22, 0.4);
}
.trace-text {
  font-size: 11px;
  color: #d1d5db;
  line-height: 1.5;
}

.notification-block {
  background: #0f172a;
  border: 1px solid rgba(6, 182, 212, 0.3);
  border-radius: 4px;
  padding: 10px;
  color: #d1d5db;
  white-space: pre-wrap;
  font-family: "JetBrains Mono", "Consolas", monospace;
  font-size: 11px;
  line-height: 1.6;
  max-height: 180px;
  overflow-y: auto;
}

.live-dot {
  width: 6px;
  height: 6px;
  background: #10b981;
  border-radius: 50%;
  display: inline-block;
  animation: blink 1.5s infinite;
}
@keyframes blink {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}
</style>
