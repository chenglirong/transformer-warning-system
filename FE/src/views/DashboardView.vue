<template>
  <div class="h-screen flex flex-col">
    <AppHeader
      title="变 压 器 智 能 预 警 系 统"
      subtitle="检测 · 预测 · 决策 · LangChain Agent"
      :show-back="false"
      large
    />

    <!-- KPI Row -->
    <section class="px-3 pt-3 grid grid-cols-5 gap-3">
      <KpiCard v-for="k in kpis" :key="k.label">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">{{ k.label }}</p>
            <p class="text-2xl font-bold" :class="k.valueClass">
              <CountUp :endValue="k.value" :duration="1600" /><span
                class="text-xs ml-1"
                >{{ k.unit }}</span
              >
            </p>
          </div>
          <iconify-icon
            class="text-3xl"
            :class="[k.iconClass, k.pulse ? 'pulse' : '']"
            :icon="k.icon"
          ></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">{{ k.hint }}</p>
      </KpiCard>
    </section>

    <main
      class="flex-1 grid grid-cols-12 gap-3 p-3 overflow-hidden"
      style="min-height: 0"
    >
      <!-- LEFT col-3: 3 charts stacked -->
      <div class="col-span-3 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 1">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-1">
            <iconify-icon icon="mdi:chart-donut"></iconify-icon>
            4 级预警分布
            <span class="plan-badge">规划中</span>
          </h3>
          <div class="w-full" style="height: calc(100% - 24px)">
            <EChart :option="levelDonutOption" />
          </div>
        </div>

        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 1.3">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-1">
            <iconify-icon icon="mdi:radar"></iconify-icon>
            DGA 7 气体异常雷达（vs 阈值）
          </h3>
          <div class="w-full" style="height: calc(100% - 24px)">
            <EChart :option="gasRadarOption" />
          </div>
        </div>

        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 1">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-1">
            <iconify-icon icon="mdi:chart-bar-stacked"></iconify-icon>
            24h 预警时段分布
            <span class="plan-badge">规划中</span>
          </h3>
          <div class="w-full" style="height: calc(100% - 24px)">
            <EChart :option="hourBarOption" />
          </div>
        </div>
      </div>

      <!-- CENTER col-6: prediction (large) + detection + conditions gauges -->
      <div class="col-span-6 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 1.7">
          <h3
            class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between"
          >
            <span class="flex items-center gap-2">
              <iconify-icon
                icon="mdi:chart-timeline-variant-shimmer"
              ></iconify-icon>
              DGA 7 气体LSTM 预测曲线（30 天历史 + 3 天预测）
              <span class="plan-badge">规划中</span>
            </span>
            <span class="flex items-center gap-3 text-[10px]">
              <span class="flex items-center gap-1">
                <span class="legend-line"></span> 真实
              </span>
              <span class="flex items-center gap-1">
                <span class="legend-line dashed"></span> 预测
              </span>
              <span class="flex items-center gap-1">
                <span class="legend-area"></span> 预测区
              </span>
              <RouterLink
                to="/prediction"
                class="text-gray-500 hover:text-cyan-400"
                >对比详情 →</RouterLink
              >
            </span>
          </h3>
          <div class="w-full" style="height: calc(100% - 28px)">
            <EChart :option="predictOption" />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3 overflow-hidden" style="flex: 1">
          <!-- Detection consistency (3 methods) -->
          <div class="glass rounded-lg p-3 flex flex-col overflow-hidden">
            <h3
              class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between"
            >
              <span class="flex items-center gap-2">
                <iconify-icon icon="mdi:eye-check"></iconify-icon>
                异常检测
              </span>
              <RouterLink
                to="/detection"
                class="text-[10px] text-gray-500 hover:text-cyan-400"
                >对比 →</RouterLink
              >
            </h3>
            <div class="flex-1 grid grid-cols-3 gap-2" style="min-height: 0">
              <div
                v-for="m in detection"
                :key="m.name"
                class="detect-cell"
                :class="m.cls"
              >
                <iconify-icon
                  class="text-2xl"
                  :class="m.iconClass"
                  :icon="m.icon"
                ></iconify-icon>
                <p class="text-[10px] text-gray-400 mt-1">{{ m.name }}</p>
                <p class="text-[11px] font-bold mt-0.5" :class="m.resultClass">
                  {{ m.result }}
                </p>
              </div>
            </div>
            <div
              class="mt-2 px-2 py-1.5 rounded text-[11px] flex items-center justify-between"
              :class="fusionConclusion.cls"
            >
              <span class="text-gray-400">融合结论</span>
              <span class="font-bold" :class="fusionConclusion.textClass">
                {{ fusionConclusion.text }}
              </span>
            </div>
          </div>

          <!-- Operating conditions gauges -->
          <div class="glass rounded-lg p-3 flex flex-col overflow-hidden">
            <h3
              class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between"
            >
              <span class="flex items-center gap-2">
                <iconify-icon icon="mdi:gauge"></iconify-icon>
                数据检测
              </span>
              <RouterLink
                to="/analysis"
                class="text-[10px] text-gray-500 hover:text-cyan-400"
                >详情 →</RouterLink
              >
            </h3>
            <div class="flex-1 grid grid-cols-3 gap-1" style="min-height: 0">
              <div
                v-for="(g, i) in conditionGauges"
                :key="i"
                class="flex flex-col"
                style="min-height: 0"
              >
                <div class="flex-1" style="min-height: 0">
                  <EChart :option="g.option" />
                </div>
                <p class="text-[10px] text-gray-500 text-center -mt-1">
                  {{ g.label }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- RIGHT col-3: Agent + C2H2 focus + scrollable alerts -->
      <div class="col-span-3 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 1">
          <h3
            class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between"
          >
            <span class="flex items-center gap-2">
              <iconify-icon icon="mdi:robot-outline"></iconify-icon>
              Agent 流水线（5 步）
              <span class="plan-badge">规划中</span>
            </span>
            <span class="text-[10px] text-green-400 flex items-center gap-1">
              <span class="live-dot"></span> 09:00 完成
            </span>
          </h3>
          <div class="agent-pipe" style="height: calc(100% - 28px)">
            <div
              v-for="(s, i) in agentSteps"
              :key="i"
              class="agent-step"
              :class="s.cls"
            >
              <div class="agent-step-num">{{ i + 1 }}</div>
              <div class="agent-step-title">{{ s.title }}</div>
              <div
                v-if="i < agentSteps.length - 1"
                class="agent-step-connector"
              ></div>
            </div>
          </div>
        </div>

        <!-- Key metric focus (switchable gas tabs) -->
        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 0.9">
          <h3
            class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between"
          >
            <span class="flex items-center gap-2">
              <iconify-icon icon="mdi:flash-alert"></iconify-icon>
              DGA 7 气体指标（距阈值）
              <span class="plan-badge">含预测·规划中</span>
            </span>
            <div class="metric-tabs">
              <button
                v-for="g in metricGases"
                :key="g.sym"
                class="metric-tab"
                :class="{ active: selectedMetric === g.sym }"
                @click="selectedMetric = g.sym"
              >
                {{ g.sym }}
              </button>
            </div>
          </h3>
          <div class="key-metric-box">
            <div class="flex items-baseline gap-2">
              <span
                class="text-5xl font-bold leading-none"
                :class="currentMetric.valueClass"
                >{{ currentMetric.value }}</span
              >
              <span class="text-sm text-gray-400">ppm</span>
              <span
                class="text-[11px] ml-auto flex items-center gap-1"
                :class="currentMetric.trendClass"
              >
                <iconify-icon :icon="currentMetric.trendIcon"></iconify-icon>
                {{ currentMetric.trend }}
              </span>
            </div>
            <div class="mt-3">
              <div class="flex justify-between text-[10px] text-gray-400 mb-1">
                <span>当前 {{ currentMetric.value }}</span>
                <span>报警阈值 {{ currentMetric.threshold }} ppm</span>
              </div>
              <div class="threshold-bar">
                <div
                  class="threshold-fill"
                  :style="{
                    width:
                      Math.min(
                        (currentMetric.value / currentMetric.threshold) * 100,
                        100,
                      ) + '%',
                  }"
                ></div>
                <div class="threshold-marker" style="left: 100%">
                  <iconify-icon
                    icon="mdi:flag"
                    class="text-red-400"
                  ></iconify-icon>
                </div>
              </div>
              <p class="text-[10px] text-gray-500 mt-1.5">
                LSTM 预测 D+3 →
                <span class="font-bold" :class="currentMetric.predictClass">
                  {{ currentMetric.predict }} ppm
                </span>
                {{ currentMetric.predictHint }}
              </p>
            </div>
          </div>
        </div>

        <!-- Active alerts (scrollable) -->
        <div
          class="glass rounded-lg p-3 flex flex-col overflow-hidden"
          style="flex: 1.2"
        >
          <h3
            class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between"
          >
            <span class="flex items-center gap-2">
              <iconify-icon icon="mdi:fire"></iconify-icon>
              活跃预警（{{ allAlerts.length }} 条）
              <span class="plan-badge">规划中</span>
            </span>
            <RouterLink
              to="/alerts"
              class="text-[10px] text-gray-500 hover:text-cyan-400"
              >处置 →</RouterLink
            >
          </h3>
          <div
            class="marquee-wrap flex-1 overflow-hidden"
            style="min-height: 0"
          >
            <div class="marquee space-y-1.5">
              <div
                v-for="(a, i) in marqueeAlerts"
                :key="i"
                class="bg-gray-800/40 border-l-4 rounded p-2"
                :class="a.border"
              >
                <div class="flex items-center justify-between">
                  <span
                    class="text-[10px] px-1.5 py-0.5 rounded font-bold"
                    :class="a.tag"
                    >{{ a.level }}</span
                  >
                  <span class="text-[10px] text-gray-500 font-mono">{{
                    a.time
                  }}</span>
                </div>
                <p class="text-[11px] text-gray-100 leading-snug mt-1">
                  {{ a.msg }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <AppFooter />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { RouterLink } from "vue-router";
import { getOverview, getLatest, getDetectMethods } from "@/service/api";
import AppHeader from "@/components/AppHeader.vue";
import AppFooter from "@/components/AppFooter.vue";
import KpiCard from "@/components/KpiCard.vue";
import CountUp from "@/components/CountUp.vue";
import EChart from "@/components/EChart.vue";
import { AXIS, TT } from "@/utils/chartDefaults";

// ============ 真实数据状态(来自后端,异步加载)============
// overview: /data/overview;latest: /data/latest/1;detectResult: /detect/methods/1
const overview = ref(null);
const latest = ref(null);
const detectResult = ref(null);
const TRANSFORMER_ID = 1; // 单设备方案(CLAUDE.md 数据事实)

onMounted(async () => {
  // 三个接口独立 try,任一失败不影响其余块展示
  try {
    overview.value = await getOverview();
  } catch (e) {
    console.warn("[Dashboard] overview 拉取失败", e);
  }
  try {
    latest.value = await getLatest(TRANSFORMER_ID);
  } catch (e) {
    console.warn("[Dashboard] latest 拉取失败", e);
  }
  try {
    detectResult.value = await getDetectMethods(TRANSFORMER_ID);
  } catch (e) {
    console.warn("[Dashboard] detect 拉取失败", e);
  }
});

// ① KPI 行:接 overview 真值。前 4 格真实,第 5 格(Agent)标规划中。
// 原「4 级预警条数」依赖第 11-12 周预警模块,改为 overview 能提供的真实指标。
const kpis = computed(() => {
  const o = overview.value;
  const healthPct = o ? +(o.history_health_ratio * 100).toFixed(1) : 0;
  const latestAbn = o ? o.latest_snapshot.abnormal : 0;
  return [
    {
      label: "监测设备",
      value: o ? o.total_transformers : 0,
      unit: "台",
      icon: "mdi:transmission-tower",
      iconClass: "text-cyan-400",
      valueClass: "text-cyan-300",
      hint: "单台虚拟变压器 · 360 天时序",
      pulse: false,
    },
    {
      label: "监测记录",
      value: o ? o.total_records : 0,
      unit: "条",
      icon: "mdi:database",
      iconClass: "text-blue-400",
      valueClass: "text-blue-300",
      hint: o ? `${o.date_range.start} ~ ${o.date_range.end}` : "加载中",
      pulse: false,
    },
    {
      label: "历史健康率",
      value: healthPct,
      unit: "%",
      icon: "mdi:heart-pulse",
      iconClass: "text-green-400",
      valueClass: "text-green-300",
      hint: "健康天数占比(二分类口径)",
      pulse: false,
    },
    {
      label: "最新状态",
      value: latestAbn,
      unit: "异常",
      icon: latestAbn ? "mdi:alert" : "mdi:check-circle",
      iconClass: latestAbn ? "text-red-400" : "text-green-400",
      valueClass: latestAbn ? "text-red-400" : "text-green-300",
      hint: "最新快照 is_abnormal 二分类",
      pulse: !!latestAbn,
    },
    {
      label: "Agent 今日执行",
      value: 0,
      unit: "次",
      icon: "mdi:robot",
      iconClass: "text-purple-400/50",
      valueClass: "text-purple-400/50",
      hint: "⏳ 规划中 · 第 13 周",
      pulse: false,
    },
  ];
});

// === 4 级饼图 ===
const levelDonutOption = {
  tooltip: { trigger: "item", ...TT },
  legend: {
    bottom: 0,
    textStyle: { color: "#9ca3af", fontSize: 10 },
    itemWidth: 8,
    itemHeight: 8,
  },
  series: [
    {
      type: "pie",
      radius: ["48%", "72%"],
      center: ["50%", "44%"],
      avoidLabelOverlap: true,
      label: {
        color: "#cbd5e1",
        fontSize: 10,
        formatter: "{b}\n{c}",
      },
      data: [
        { value: 1, name: "红", itemStyle: { color: "#ef4444" } },
        { value: 3, name: "橙", itemStyle: { color: "#f97316" } },
        { value: 4, name: "黄", itemStyle: { color: "#eab308" } },
        { value: 2, name: "蓝", itemStyle: { color: "#3b82f6" } },
      ],
    },
  ],
};

// === ② 气体雷达:当前值接 latest.gases 真值,阈值线为国标固定值 ===
const GAS_KEYS = ["h2", "ch4", "c2h6", "c2h4", "c2h2", "co", "co2"]; // 对应雷达 7 维顺序
const gasRadarOption = computed(() => ({
  tooltip: { ...TT },
  radar: {
    indicator: [
      { name: "H₂", max: 150 },
      { name: "CH₄", max: 100 },
      { name: "C₂H₆", max: 50 },
      { name: "C₂H₄", max: 100 },
      { name: "C₂H₂", max: 5 },
      { name: "CO", max: 500 },
      { name: "CO₂", max: 2000 },
    ],
    splitNumber: 3,
    center: ["50%", "52%"],
    radius: "62%",
    name: { textStyle: { color: "#cbd5e1", fontSize: 10 } },
    splitLine: { lineStyle: { color: "rgba(107,114,128,.25)" } },
    splitArea: {
      areaStyle: { color: ["rgba(59,130,246,.02)", "rgba(59,130,246,.06)"] },
    },
    axisLine: { lineStyle: { color: "rgba(59,130,246,.25)" } },
  },
  series: [
    {
      type: "radar",
      data: [
        {
          value: [150, 100, 50, 100, 5, 500, 2000],
          name: "阈值",
          areaStyle: { color: "rgba(239,68,68,.08)" },
          lineStyle: { type: "dashed", color: "#ef4444" },
          itemStyle: { color: "#ef4444" },
        },
        {
          value: latest.value
            ? GAS_KEYS.map((k) => latest.value.gases[k])
            : [0, 0, 0, 0, 0, 0, 0],
          name: "当前",
          areaStyle: { color: "rgba(6,182,212,.25)" },
          lineStyle: { color: "#06b6d4" },
          itemStyle: { color: "#06b6d4" },
        },
      ],
    },
  ],
}));

// === 24h 预警时段分布（4级堆叠条）===
const hourBarOption = {
  tooltip: { trigger: "axis", ...TT },
  legend: {
    textStyle: { color: "#9ca3af", fontSize: 9 },
    top: 0,
    right: 0,
    itemWidth: 8,
    itemHeight: 6,
  },
  grid: { top: 22, bottom: 18, left: 22, right: 6 },
  xAxis: {
    type: "category",
    data: ["0", "3", "6", "9", "12", "15", "18", "21"],
    ...AXIS,
    axisLabel: { ...AXIS.axisLabel, fontSize: 9 },
  },
  yAxis: {
    type: "value",
    ...AXIS,
    axisLabel: { ...AXIS.axisLabel, fontSize: 9 },
  },
  series: [
    {
      name: "红",
      type: "bar",
      stack: "x",
      data: [0, 0, 1, 0, 0, 0, 0, 0],
      itemStyle: { color: "#ef4444" },
    },
    {
      name: "橙",
      type: "bar",
      stack: "x",
      data: [0, 0, 1, 1, 1, 0, 0, 0],
      itemStyle: { color: "#f97316" },
    },
    {
      name: "黄",
      type: "bar",
      stack: "x",
      data: [0, 0, 0, 1, 1, 1, 1, 0],
      itemStyle: { color: "#eab308" },
    },
    {
      name: "蓝",
      type: "bar",
      stack: "x",
      data: [1, 0, 1, 0, 0, 0, 0, 0],
      itemStyle: { color: "#3b82f6" },
    },
  ],
};

// === ③ 检测:接 /detect/methods/1 真值(规则法:阈值 + 三比值)===
// 后端单点只跑规则类两法(阈值/IEC),孤立森林是批量无监督方法不适合单点,
// 见 api/detect.py 注释;孤立森林结果在 DetectionView 全量对比中展示。
// 守边界:只显示「异常/正常」二分类,绝不显示 IEC 推出的故障类型。
const abnTag = (isAbn) =>
  isAbn
    ? { result: "异常", resultClass: "text-red-300", iconClass: "text-red-400", cls: "bad" }
    : { result: "正常", resultClass: "text-green-300", iconClass: "text-green-400", cls: "ok" };

const detection = computed(() => {
  const r = detectResult.value;
  const th = r ? r.methods.threshold.is_abnormal : false;
  const ie = r ? r.methods.iec.is_abnormal : false;
  return [
    { name: "阈值法", icon: "mdi:tune-vertical", ...abnTag(th) },
    { name: "三比值法", icon: "mdi:calculator-variant", ...abnTag(ie) },
    {
      name: "孤立森林",
      icon: "mdi:pine-tree",
      result: "批量法",
      resultClass: "text-gray-500",
      iconClass: "text-gray-500",
      cls: "neutral",
    },
  ];
});

const fusionConclusion = computed(() => {
  const r = detectResult.value;
  if (!r) return { text: "加载中…", textClass: "text-gray-400", cls: "bg-gray-500/10 border border-gray-500/30" };
  const { abnormal_count, total, is_abnormal } = r.vote;
  return is_abnormal
    ? {
        text: `异常（${abnormal_count}/${total} 规则触发）`,
        textClass: "text-red-300",
        cls: "bg-red-500/10 border border-red-500/30",
      }
    : {
        text: `正常（${abnormal_count}/${total} 规则触发）`,
        textClass: "text-green-300",
        cls: "bg-green-500/10 border border-green-500/30",
      };
});

// === 工况 4 mini gauge ===
const buildGauge = (value, max, unit, color) => ({
  series: [
    {
      type: "gauge",
      center: ["50%", "55%"],
      radius: "82%",
      min: 0,
      max,
      splitNumber: 4,
      progress: { show: true, width: 6, itemStyle: { color } },
      axisLine: { lineStyle: { width: 6, color: [[1, "rgba(75,85,99,.4)"]] } },
      pointer: { show: false },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      title: { show: false },
      detail: {
        valueAnimation: true,
        offsetCenter: [0, "5%"],
        fontSize: 16,
        fontWeight: "bold",
        color,
        formatter: `{value}${unit}`,
      },
      data: [{ value, name: unit }],
    },
  ],
});

// === ④ 工况仪表:接 latest.conditions 真值(油温/负载电流/环温)===
// 后端只有这 3 个工况字段;原「温升 ℃/h」无数据来源,去掉。
const conditionGauges = computed(() => {
  const c = latest.value ? latest.value.conditions : null;
  const r1 = (x) => (x == null ? 0 : +x.toFixed(1));
  return [
    { label: "油温 / 95℃", option: buildGauge(r1(c?.oil_temp), 95, "℃", "#10b981") },
    { label: "负载电流 / 250A", option: buildGauge(r1(c?.load_current), 250, "A", "#f97316") },
    { label: "环温 / 45℃", option: buildGauge(r1(c?.ambient_temp), 45, "℃", "#eab308") },
  ];
});

// === LSTM 预测大图 ===
const historyDays = Array.from({ length: 30 }, (_, i) => `D-${29 - i}`);
const futureDays = ["D+1", "D+2", "D+3"];
const xAxisData = [...historyDays, ...futureDays];

const genSeries = (history, forecast) => {
  const realPart = [...history, ...Array(3).fill(null)];
  const connectForecast = [...Array(29).fill(null), history[29], ...forecast];
  return { realPart, connectForecast };
};

const genHistory = (start, end, wave = 0.05) =>
  Array.from({ length: 30 }, (_, i) => {
    const t = i / 29;
    const v = start + (end - start) * t;
    return +(
      v *
      (1 + (Math.sin(i * 0.7) + (Math.random() - 0.5) * 0.5) * wave)
    ).toFixed(2);
  });

const hC2H2 = [
  0.8, 0.9, 1.0, 1.1, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1,
  2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 3.0, 3.05, 3.1, 3.15, 3.2, 3.22, 3.24,
];

const gasConfig = [
  {
    sym: "H₂",
    color: "#10b981",
    history: genHistory(25, 42.5),
    forecast: [43.8, 45.2, 46.5],
  },
  {
    sym: "CH₄",
    color: "#06b6d4",
    history: genHistory(35, 58.2),
    forecast: [59.4, 60.9, 62.5],
  },
  {
    sym: "C₂H₆",
    color: "#8b5cf6",
    history: genHistory(15, 22.8),
    forecast: [23.2, 23.8, 24.1],
  },
  {
    sym: "C₂H₄",
    color: "#f59e0b",
    history: genHistory(22, 45.1),
    forecast: [46.2, 47.8, 49.5],
  },
  {
    sym: "CO",
    color: "#a3e635",
    history: genHistory(260, 312),
    forecast: [316, 321, 325],
  },
  {
    sym: "CO₂",
    color: "#f472b6",
    history: genHistory(1500, 1840),
    forecast: [1860, 1885, 1910],
  },
  {
    sym: "C₂H₂",
    color: "#ef4444",
    history: hC2H2,
    forecast: [3.42, 3.68, 4.05],
    axis: 1,
  },
];

const buildSeries = () => {
  const series = [];
  gasConfig.forEach((g) => {
    const split = genSeries(g.history, g.forecast);
    const axisIdx = g.axis || 0;
    series.push({
      name: `${g.sym}（真）`,
      type: "line",
      smooth: true,
      data: split.realPart,
      color: g.color,
      yAxisIndex: axisIdx,
      symbol: "none",
      lineStyle: { width: g.sym === "C₂H₂" ? 2.2 : 1.6 },
    });
    series.push({
      name: `${g.sym}（预）`,
      type: "line",
      smooth: true,
      data: split.connectForecast,
      color: g.color,
      yAxisIndex: axisIdx,
      symbol: "circle",
      symbolSize: 4,
      lineStyle: { type: "dashed", width: g.sym === "C₂H₂" ? 2 : 1.6 },
      ...(g.sym === "C₂H₂"
        ? {
            markLine: {
              symbol: "none",
              data: [
                {
                  yAxis: 5,
                  lineStyle: { color: "#dc2626", type: "dashed" },
                  label: {
                    formatter: "C₂H₂ 报警 5 ppm",
                    color: "#fca5a5",
                    fontSize: 10,
                  },
                },
              ],
            },
            markArea: {
              itemStyle: { color: "rgba(251,146,60,.1)" },
              data: [[{ xAxis: "D-0" }, { xAxis: "D+3" }]],
            },
          }
        : {}),
    });
  });
  return series;
};

const predictOption = {
  tooltip: { trigger: "axis", ...TT },
  legend: {
    textStyle: { color: "#9ca3af", fontSize: 9 },
    top: 0,
    right: 90,
    type: "scroll",
    itemWidth: 10,
    itemHeight: 6,
  },
  grid: { top: 35, bottom: 30, left: 40, right: 60 },
  xAxis: {
    type: "category",
    data: xAxisData,
    ...AXIS,
    axisLabel: { ...AXIS.axisLabel, interval: 3 },
  },
  yAxis: [
    {
      type: "value",
      name: "ppm",
      nameTextStyle: { color: "#9ca3af", fontSize: 10 },
      ...AXIS,
    },
    {
      type: "value",
      name: "C₂H₂",
      nameTextStyle: { color: "#ef4444", fontSize: 10 },
      ...AXIS,
      max: 6,
    },
  ],
  series: buildSeries(),
};

// === Agent 5 步流水线 ===
const agentSteps = [
  { title: "获取数据", cls: "done" },
  { title: "异常检测", cls: "done" },
  { title: "LSTM 预测", cls: "done" },
  { title: "规则判级", cls: "done" },
  { title: "生成通知", cls: "done" },
];

// === 关键指标聚焦（7 气体可切换）===
const metricGases = [
  {
    sym: "C₂H₂",
    value: 3.24,
    threshold: 5,
    trend: "7d ↑ 18%",
    trendIcon: "mdi:trending-up",
    trendClass: "text-red-300",
    valueClass: "text-red-400",
    predict: 4.05,
    predictClass: "text-red-300",
    predictHint: "（已逼近阈值）",
  },
  {
    sym: "H₂",
    value: 42.5,
    threshold: 150,
    trend: "7d ↑ 5%",
    trendIcon: "mdi:trending-up",
    trendClass: "text-yellow-300",
    valueClass: "text-yellow-400",
    predict: 46.5,
    predictClass: "text-yellow-300",
    predictHint: "",
  },
  {
    sym: "CH₄",
    value: 58.2,
    threshold: 100,
    trend: "7d ↑ 38%",
    trendIcon: "mdi:trending-up",
    trendClass: "text-orange-300",
    valueClass: "text-orange-400",
    predict: 62.5,
    predictClass: "text-orange-300",
    predictHint: "",
  },
  {
    sym: "C₂H₆",
    value: 22.8,
    threshold: 50,
    trend: "7d ↑ 27%",
    trendIcon: "mdi:trending-up",
    trendClass: "text-yellow-300",
    valueClass: "text-yellow-400",
    predict: 24.1,
    predictClass: "text-yellow-300",
    predictHint: "",
  },
  {
    sym: "C₂H₄",
    value: 45.1,
    threshold: 100,
    trend: "7d ↑ 23%",
    trendIcon: "mdi:trending-up",
    trendClass: "text-orange-300",
    valueClass: "text-orange-400",
    predict: 49.5,
    predictClass: "text-orange-300",
    predictHint: "（趋势异常）",
  },
  {
    sym: "CO",
    value: 312,
    threshold: 500,
    trend: "7d ↑ 3%",
    trendIcon: "mdi:trending-up",
    trendClass: "text-green-300",
    valueClass: "text-green-400",
    predict: 325,
    predictClass: "text-green-300",
    predictHint: "",
  },
  {
    sym: "CO₂",
    value: 1840,
    threshold: 2000,
    trend: "7d ↑ 2%",
    trendIcon: "mdi:trending-up",
    trendClass: "text-yellow-300",
    valueClass: "text-yellow-400",
    predict: 1910,
    predictClass: "text-yellow-300",
    predictHint: "",
  },
];

const selectedMetric = ref("C₂H₂");
const currentMetric = computed(
  () =>
    metricGases.find((g) => g.sym === selectedMetric.value) || metricGases[0],
);

// === 活跃预警列表（滚动，含所有 10 条）===
const allAlerts = [
  {
    level: "🔴 红",
    tag: "tag-red",
    border: "border-red-500",
    time: "10:42",
    msg: "C₂H₂ 预测 D+3 达 4.05 ppm，逼近阈值 5 ppm",
  },
  {
    level: "🟠 橙",
    tag: "tag-org",
    border: "border-orange-500",
    time: "10:15",
    msg: "C₂H₄ 72h 上升 23%，1-3 天内可能超标",
  },
  {
    level: "🟠 橙",
    tag: "tag-org",
    border: "border-orange-500",
    time: "09:58",
    msg: "顶层油温 84℃ + 负载 1.05 倍，组合规则触发",
  },
  {
    level: "🟠 橙",
    tag: "tag-org",
    border: "border-orange-500",
    time: "09:30",
    msg: "多方法投票判定为异常(三比值法 + 阈值法)",
  },
  {
    level: "🟡 黄",
    tag: "tag-yel",
    border: "border-yellow-500",
    time: "08:50",
    msg: "H₂ 产气速率 8.2 ppm/72h，趋势异常",
  },
  {
    level: "🟡 黄",
    tag: "tag-yel",
    border: "border-yellow-500",
    time: "07:22",
    msg: "负载电流 1.05 倍额定（长期）",
  },
  {
    level: "🟡 黄",
    tag: "tag-yel",
    border: "border-yellow-500",
    time: "06:45",
    msg: "C₂H₆ 7 日上升 27%",
  },
  {
    level: "🟡 黄",
    tag: "tag-yel",
    border: "border-yellow-500",
    time: "05:30",
    msg: "总烃 7 日 ↑ 18%",
  },
  {
    level: "🔵 蓝",
    tag: "tag-blu",
    border: "border-blue-500",
    time: "04:10",
    msg: "环境温度 38℃ 接近 40℃ 阈值",
  },
  {
    level: "🔵 蓝",
    tag: "tag-blu",
    border: "border-blue-500",
    time: "02:30",
    msg: "CO 轻微波动 +5%",
  },
];

const marqueeAlerts = computed(() => [...allAlerts, ...allAlerts]);
</script>

<style scoped>
.legend-line {
  width: 18px;
  height: 2px;
  background: #06b6d4;
  display: inline-block;
}
.legend-line.dashed {
  background: repeating-linear-gradient(
    90deg,
    #06b6d4 0 4px,
    transparent 4px 7px
  );
}

.legend-area {
  width: 14px;
  height: 10px;
  background: rgba(251, 146, 60, 0.25);
  border: 1px solid rgba(251, 146, 60, 0.5);
  display: inline-block;
}

.detect-cell {
  background: rgba(31, 41, 55, 0.55);
  border: 1px solid rgba(75, 85, 99, 0.4);
  border-radius: 6px;
  padding: 8px;
  text-align: center;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.detect-cell.bad {
  border-color: rgba(239, 68, 68, 0.5);
  background: rgba(239, 68, 68, 0.06);
}

/* 规划中徽章:标注尚未开发的模块(第 9-13 周),与中期检查"诚实展示"原则一致 */
.plan-badge {
  display: inline-block;
  margin-left: 6px;
  font-size: 9px;
  font-weight: 500;
  color: #fcd34d;
  background: rgba(234, 179, 8, 0.12);
  border: 1px solid rgba(234, 179, 8, 0.35);
  padding: 1px 6px;
  border-radius: 10px;
  vertical-align: middle;
  white-space: nowrap;
}

/* Agent 流水线 */
.agent-pipe {
  display: flex;
  flex-direction: column;
  justify-content: space-around;
  padding: 4px 0;
}
.agent-step {
  display: flex;
  align-items: center;
  gap: 10px;
  position: relative;
}
.agent-step-num {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 12px;
  flex-shrink: 0;
  background: rgba(16, 185, 129, 0.18);
  color: #6ee7b7;
  border: 2px solid #10b981;
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.5);
  position: relative;
  z-index: 2;
}
.agent-step.done .agent-step-num::after {
  content: "✓";
  position: absolute;
  bottom: -2px;
  right: -4px;
  background: #10b981;
  color: white;
  font-size: 9px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.agent-step-title {
  flex: 1;
  font-size: 12px;
  color: #d1d5db;
  font-weight: 500;
}
.agent-step-connector {
  position: absolute;
  left: 13px;
  top: 28px;
  bottom: -100%;
  width: 2px;
  background: linear-gradient(180deg, #10b981 0%, rgba(16, 185, 129, 0.3) 100%);
}

/* C2H2 关键指标条 */
.key-metric-box {
  padding: 4px 2px;
}
.threshold-bar {
  position: relative;
  height: 10px;
  background: linear-gradient(
    90deg,
    rgba(16, 185, 129, 0.3) 0%,
    rgba(245, 158, 11, 0.3) 60%,
    rgba(239, 68, 68, 0.4) 100%
  );
  border: 1px solid rgba(75, 85, 99, 0.4);
  border-radius: 5px;
  overflow: visible;
}
.threshold-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981 0%, #f59e0b 60%, #ef4444 100%);
  border-radius: 4px;
}
.threshold-marker {
  position: absolute;
  top: -10px;
  transform: translateX(-50%);
  font-size: 14px;
}

/* 指标 tab 切换 */
.metric-tabs {
  display: flex;
  gap: 2px;
  background: rgba(31, 41, 55, 0.5);
  border-radius: 4px;
  padding: 2px;
}
.metric-tab {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 3px;
  color: #9ca3af;
  transition: all 0.15s;
  cursor: pointer;
  background: transparent;
  border: none;
  font-family: inherit;
}
.metric-tab:hover {
  color: #e5e7eb;
  background: rgba(59, 130, 246, 0.15);
}
.metric-tab.active {
  background: rgba(6, 182, 212, 0.2);
  color: #67e8f9;
  border: 1px solid rgba(6, 182, 212, 0.4);
  padding: 1px 5px;
}

.marquee-wrap:hover .marquee {
  animation-play-state: paused;
}
.marquee {
  animation: marquee-scroll 25s linear infinite;
}
@keyframes marquee-scroll {
  0% {
    transform: translateY(0);
  }
  100% {
    transform: translateY(-50%);
  }
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10b981;
  display: inline-block;
  animation: livePulse 2s ease-in-out infinite;
}
@keyframes livePulse {
  0%,
  100% {
    opacity: 1;
    box-shadow: 0 0 4px rgba(16, 185, 129, 0.6);
  }
  50% {
    opacity: 0.4;
    box-shadow: none;
  }
}
</style>
