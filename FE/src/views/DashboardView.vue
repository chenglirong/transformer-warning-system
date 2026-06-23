<template>
  <div class="h-screen flex flex-col">
    <AppHeader
      title="变 压 器 智 能 预 警 系 统"
      subtitle="检测 · 预测 · 决策 · LangChain Agent"
      :show-back="false"
      large
    />

    <!-- KPI Row -->
    <section class="px-3 pt-3 grid grid-cols-4 gap-3">
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
      <!-- ========== 左栏:状态概览(此刻这台设备什么状态)========== -->
      <!-- 雷达(当前气体)→ 检测融合(当前判定)→ 工况(实时)→ 健康带(全周期)-->
      <div class="col-span-3 flex flex-col gap-3 overflow-hidden">
        <!-- 异常检测(三方法融合)-->
        <div class="glass rounded-lg p-3 flex flex-col overflow-hidden" style="flex: 1">
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

        <!-- 全周期健康/异常分布 -->
        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 1">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-1">
            <iconify-icon icon="mdi:chart-bar-stacked"></iconify-icon>
            全周期健康/异常分布（按月）
          </h3>
          <div class="w-full" style="height: calc(100% - 24px)">
            <EChart :option="healthBandOption" />
          </div>
        </div>
      </div>

      <!-- ========== 中栏:核心趋势(走势与预测)========== -->
      <!-- ARIMA 趋势预测大图(独占,聚焦趋势)-->
      <div class="col-span-6 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 1.7">
          <h3
            class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between"
          >
            <span class="flex items-center gap-2">
              <iconify-icon
                icon="mdi:chart-timeline-variant-shimmer"
              ></iconify-icon>
              DGA 7 气体 ARIMA 趋势预测(30 天历史 + 未来 3 天)
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

        <!-- DGA 气体指标卡(当前值 + ARIMA 预测),7 气体可切换 -->
        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 1">
          <h3
            class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between"
          >
            <span class="flex items-center gap-2 whitespace-nowrap">
              <iconify-icon icon="mdi:flash-alert"></iconify-icon>
              DGA 气体指标
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
                >{{ currentMetric.value ?? "—" }}</span
              >
              <span class="text-sm text-gray-400">μL/L</span>
            </div>
            <div class="mt-3">
              <!-- 有国标注意值(H₂/C₂H₂/总烃):显距阈值进度条 -->
              <template v-if="currentMetric.threshold != null">
                <div class="flex justify-between text-[10px] text-gray-400 mb-1">
                  <span>当前 {{ currentMetric.value ?? "—" }}</span>
                  <span>注意值 {{ currentMetric.threshold }} μL/L</span>
                </div>
                <div class="threshold-bar">
                  <div
                    class="threshold-fill"
                    :style="{
                      width:
                        Math.min(
                          ((currentMetric.value || 0) / currentMetric.threshold) * 100,
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
              </template>
              <!-- CO/CO₂/单个烃类:国标表3 未设绝对注意值(D-044)-->
              <p v-else class="text-[10px] text-gray-500">
                国标 DL/T 722-2014 表3 未设单气体注意值
              </p>
              <p class="text-[10px] text-gray-500 mt-1.5">
                ARIMA 预测 D+3 →
                <span class="font-bold" :class="currentMetric.predictClass">
                  {{ currentMetric.predict ?? "—" }} μL/L
                </span>
                {{ currentMetric.predictHint }}
              </p>
            </div>
          </div>
        </div>

      </div>

      <!-- ========== 右栏:预警处置(预警 → 处置动作)========== -->
      <!-- 4级等级构成 → 活跃预警工单 → LangChain Agent 自动处置 -->
      <div class="col-span-3 flex flex-col gap-3 overflow-hidden">
        <!-- 4 级预警分布(等级构成)-->
        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 1">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-1">
            <iconify-icon icon="mdi:chart-donut"></iconify-icon>
            4 级预警分布（回测）
          </h3>
          <div class="w-full" style="height: calc(100% - 24px)">
            <EChart :option="levelDonutOption" />
          </div>
        </div>

        <!-- 活跃预警工单(滚动)-->
        <div
          class="glass rounded-lg p-3 flex flex-col overflow-hidden"
          style="flex: 1.2"
        >
          <h3
            class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between"
          >
            <span class="flex items-center gap-2">
              <iconify-icon icon="mdi:fire"></iconify-icon>
              活跃预警(近 {{ allAlerts.length }} 条)
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

        <!-- LangChain Agent 流水线(自动处置)-->
        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 1">
          <h3
            class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between"
          >
            <span class="flex items-center gap-2">
              <iconify-icon icon="mdi:robot-outline"></iconify-icon>
              LangChain Agent 流水线
            </span>
            <span
              v-if="agentRun"
              class="text-[10px] text-green-400 flex items-center gap-1"
            >
              <span class="live-dot"></span>
              {{ agentRun.as_of }} · {{ (agentRun.duration_ms / 1000).toFixed(1) }}s
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
      </div>
    </main>

    <AppFooter />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { RouterLink } from "vue-router";
import {
  getOverview,
  getLatest,
  getDetectMethods,
  getDetectRecent,
  getDashboardForecast,
  getWarningBacktest,
  getDates,
  getAgentRun,
} from "@/service/api";
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
const detectRecent = ref(null); // /detect/recent:近N日三方法逐日(孤立森林最新日判定)
const forecast = ref(null);   // /predict/forecast:30 天历史 + 未来 3 天 ARIMA
const backtest = ref(null);   // /warning/backtest:真实预警工单 + 四级分布
const agentRun = ref(null);   // /agent/run:最新一条 Agent ReAct 预跑轨迹
const series360 = ref([]);    // /data/dates 全周期 date+is_abnormal:健康/异常时间带用
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
  try {
    detectRecent.value = await getDetectRecent(TRANSFORMER_ID);
  } catch (e) {
    console.warn("[Dashboard] detect recent 拉取失败", e);
  }
  try {
    forecast.value = await getDashboardForecast();
  } catch (e) {
    console.warn("[Dashboard] forecast 拉取失败(未跑预跑脚本?)", e);
  }
  try {
    backtest.value = await getWarningBacktest();
  } catch (e) {
    console.warn("[Dashboard] warning backtest 拉取失败", e);
  }
  try {
    agentRun.value = await getAgentRun(TRANSFORMER_ID);
  } catch (e) {
    console.warn("[Dashboard] agent run 拉取失败(未预跑?)", e);
  }
  try {
    // 全周期健康带:/data/dates 返回全 360 天 date+is_abnormal(无 days 上限)
    const ds = await getDates(TRANSFORMER_ID);
    series360.value = ds.days || [];
  } catch (e) {
    console.warn("[Dashboard] dates(全周期) 拉取失败", e);
  }
});

// ① KPI 行:4 张核心卡片,按权重排序,全部接真。
//   1 设备总览(合并设备数+记录数+跨度)2 历史健康率 3 当前实时状态 4 历史预警累计
//   去掉原「Agent 预警分析」格(与右侧流水线模块重复);
//   当前预警等级(最新日红橙黄蓝)与历史预警累计(360天回测)分列,口径与预警体系一致。
const kpis = computed(() => {
  const o = overview.value;
  const healthPct = o ? +(o.history_health_ratio * 100).toFixed(1) : 0;
  const nAlerts = backtest.value ? backtest.value.n_alerts : 0;
  const span = o ? `${o.date_range.start} ~ ${o.date_range.end}` : "加载中";
  // 当前(最新日)预警等级:取 backtest 最新一天 alert 的 level(红橙黄蓝四级)。
  // 无 alert = 该日未触发任何规则 → 蓝(日常关注)。与预警体系/右下工单同口径。
  const KPI_LEVEL = {
    red: { zh: "红色", cls: "text-red-400", icon: "mdi:alert-octagon", resp: "立即响应" },
    orange: { zh: "橙色", cls: "text-orange-400", icon: "mdi:alert", resp: "24 小时内处理" },
    yellow: { zh: "黄色", cls: "text-yellow-400", icon: "mdi:alert-outline", resp: "加强监测" },
    blue: { zh: "蓝色", cls: "text-blue-400", icon: "mdi:information-outline", resp: "日常关注" },
  };
  const alerts = backtest.value ? backtest.value.alerts : [];
  const lastAlert = alerts.length
    ? [...alerts].sort((a, b) => (a.date < b.date ? 1 : -1))[0]
    : null;
  const curLevel = lastAlert ? lastAlert.level : "blue";
  const lv = KPI_LEVEL[curLevel] || KPI_LEVEL.blue;
  return [
    {
      label: "设备总览",
      value: o ? o.total_transformers : 0,
      unit: "台设备",
      icon: "mdi:transmission-tower",
      iconClass: "text-cyan-400",
      valueClass: "text-cyan-300",
      hint: o ? `${o.total_records} 条时序 · ${span}` : "加载中",
      pulse: false,
    },
    {
      label: "历史健康率",
      value: healthPct,
      unit: "%",
      icon: "mdi:heart-pulse",
      iconClass: "text-green-400",
      valueClass: "text-green-300",
      hint: "360 天健康天数占比(二分类)",
      pulse: false,
    },
    {
      label: "当前预警等级",
      value: lv.zh,
      unit: "",
      icon: lv.icon,
      iconClass: lv.cls,
      valueClass: lv.cls,
      hint: lastAlert
        ? `${lastAlert.date} · ${lv.resp}`
        : `${o ? o.date_range.end : ""} · 无触发`,
      pulse: curLevel === "red",
    },
    {
      label: "历史预警累计",
      value: nAlerts,
      unit: "条",
      icon: "mdi:bell-alert",
      iconClass: "text-orange-400",
      valueClass: "text-orange-300",
      hint: "360 天回测触发工单(非实时)",
      pulse: false,
    },
  ];
});

// === ④ 4 级预警分布饼图:接 /warning/backtest 的 level_distribution 真值 ===
// 回测(360 天合成时序)各等级触发条数;数据源同 AlertsView / backtest.py。
const levelDonutOption = computed(() => {
  const dist = backtest.value ? backtest.value.level_distribution : null;
  return {
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
        label: { color: "#cbd5e1", fontSize: 10, formatter: "{b}\n{c}" },
        data: [
          { value: dist ? dist.red : 0, name: "红", itemStyle: { color: "#ef4444" } },
          { value: dist ? dist.orange : 0, name: "橙", itemStyle: { color: "#f97316" } },
          { value: dist ? dist.yellow : 0, name: "黄", itemStyle: { color: "#eab308" } },
          { value: dist ? dist.blue : 0, name: "蓝", itemStyle: { color: "#3b82f6" } },
        ],
      },
    ],
  };
});


// === ④ 全周期健康/异常分布:按月聚合 /data/timeseries 的 is_abnormal(360 天)===
// 把顶部 KPI「健康率」可视化展开为时间维度——逐月健康天 vs 异常天堆叠,
// 一眼看出全周期(2024-04~2025-03)哪些月份异常集中。与左上「等级构成饼图」
// 视角互补(一个看等级构成,一个看时间分布),不重复。数据源 series360。
const healthBandOption = computed(() => {
  const s = series360.value || [];
  // 按月聚合健康/异常天数
  const byMonth = {};
  for (const d of s) {
    const m = d.date.slice(0, 7);
    byMonth[m] = byMonth[m] || { healthy: 0, abnormal: 0 };
    if (d.is_abnormal) byMonth[m].abnormal += 1;
    else byMonth[m].healthy += 1;
  }
  const months = Object.keys(byMonth).sort();
  return {
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
      data: months.map((m) => m.slice(2)), // YY-MM 省位
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
        name: "健康",
        type: "bar",
        stack: "d",
        data: months.map((m) => byMonth[m].healthy),
        itemStyle: { color: "#10b981" },
      },
      {
        name: "异常",
        type: "bar",
        stack: "d",
        data: months.map((m) => byMonth[m].abnormal),
        itemStyle: { color: "#ef4444" },
      },
    ],
  };
});

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
  // 孤立森林是批量无监督法,单点接口不跑;取 /detect/recent 全量 fit 后最新一日的判定
  const daily = detectRecent.value ? detectRecent.value.daily : null;
  const isf = daily && daily.length ? daily[daily.length - 1].iforest : false;
  return [
    { name: "阈值法", icon: "mdi:tune-vertical", ...abnTag(th) },
    { name: "三比值法", icon: "mdi:calculator-variant", ...abnTag(ie) },
    { name: "孤立森林", icon: "mdi:pine-tree", ...abnTag(isf) },
  ];
});

const fusionConclusion = computed(() => {
  // 与检测块同口径:用 /detect/recent 最新日三方法投票(≥2 方法判异常→异常,majority)
  const daily = detectRecent.value ? detectRecent.value.daily : null;
  if (!daily || !daily.length)
    return { text: "加载中…", textClass: "text-gray-400", cls: "bg-gray-500/10 border border-gray-500/30" };
  const last = daily[daily.length - 1];
  const n = last.vote_abnormal;        // 0~3 方法判异常
  const isAbn = last.is_abnormal;      // ≥2 票为异常
  return isAbn
    ? {
        text: `异常（${n}/3 方法判异常）`,
        textClass: "text-red-300",
        cls: "bg-red-500/10 border border-red-500/30",
      }
    : {
        text: `正常（${n}/3 方法判异常）`,
        textClass: "text-green-300",
        cls: "bg-green-500/10 border border-green-500/30",
      };
});

// === ⑤ ARIMA 趋势预测大图:接 /predict/forecast 真值(30 天历史 + 未来 3 天)===
// 预测源 ARIMA(D-029:实测较 LSTM 更稳健,大屏不主打 LSTM 误导);数据离线预跑
// (scripts/forecast_dashboard.py)。C₂H₂ 量纲远小于其它气体,单列右轴 + 国标注意值线。
const GAS_VIZ = [
  { key: "h2", sym: "H₂", color: "#10b981", axis: 0 },
  { key: "ch4", sym: "CH₄", color: "#06b6d4", axis: 0 },
  { key: "c2h6", sym: "C₂H₆", color: "#8b5cf6", axis: 0 },
  { key: "c2h4", sym: "C₂H₄", color: "#f59e0b", axis: 0 },
  { key: "co", sym: "CO", color: "#a3e635", axis: 0 },
  { key: "co2", sym: "CO₂", color: "#f472b6", axis: 0 },
  { key: "c2h2", sym: "C₂H₂", color: "#ef4444", axis: 1 },
];

// x 轴:历史日期(尾部取短标 MM-DD)+ D+1..D+n
const predictXAxis = computed(() => {
  const f = forecast.value;
  if (!f) return [];
  const hist = f.history.map((r) => r.date.slice(5)); // MM-DD
  const fut = f.forecast.map((r) => `D+${r.step}`);
  return [...hist, ...fut];
});

const buildSeries = () => {
  const f = forecast.value;
  if (!f) return [];
  const nHist = f.history.length;
  const series = [];
  GAS_VIZ.forEach((g) => {
    const hist = f.history.map((r) => r[g.key]);
    const fut = f.forecast.map((r) => r[g.key]);
    // 历史实线:历史段有值,预测段 null
    const realPart = [...hist, ...Array(fut.length).fill(null)];
    // 预测虚线:用历史末点接上,视觉连续
    const connectForecast = [
      ...Array(nHist - 1).fill(null),
      hist[nHist - 1],
      ...fut,
    ];
    series.push({
      name: `${g.sym}(真)`,
      type: "line",
      smooth: true,
      data: realPart,
      color: g.color,
      yAxisIndex: g.axis,
      symbol: "none",
      lineStyle: { width: g.key === "c2h2" ? 2.2 : 1.6 },
    });
    series.push({
      name: `${g.sym}(预)`,
      type: "line",
      smooth: true,
      data: connectForecast,
      color: g.color,
      yAxisIndex: g.axis,
      symbol: "circle",
      symbolSize: 4,
      lineStyle: { type: "dashed", width: g.key === "c2h2" ? 2 : 1.6 },
      ...(g.key === "c2h2"
        ? {
            // C₂H₂ 国标注意值线(DL/T 722-2014 表3,220kV 及以下 = 5 μL/L)
            markLine: {
              symbol: "none",
              data: [
                {
                  yAxis: 5,
                  lineStyle: { color: "#dc2626", type: "dashed" },
                  label: {
                    formatter: "C₂H₂ 注意值 5 μL/L",
                    color: "#fca5a5",
                    fontSize: 10,
                  },
                },
              ],
            },
            // 预测区阴影:从历史末点到 D+n
            markArea: {
              itemStyle: { color: "rgba(251,146,60,.1)" },
              data: [
                [
                  { xAxis: predictXAxis.value[nHist - 1] },
                  { xAxis: predictXAxis.value[predictXAxis.value.length - 1] },
                ],
              ],
            },
          }
        : {}),
    });
  });
  return series;
};

const predictOption = computed(() => ({
  // tooltip:每个气体只显有值的一行(历史段真实 / 预测段预测;另一半为 null 过滤掉),
  // 去「(真)/(预)」后缀,避免 14 行里一半是「—」的空行。
  tooltip: {
    trigger: "axis",
    ...TT,
    formatter: (params) => {
      if (!params.length) return "";
      const day = params[0].axisValue;
      const seen = new Set();
      const rows = [];
      for (const p of params) {
        if (p.value == null) continue;
        // 接缝日(历史末点 = 预测起点)真实/预测两 series 同值,按气体名去重
        const gas = p.seriesName.replace(/（[真预]）|\([真预]\)/g, "");
        if (seen.has(gas)) continue;
        seen.add(gas);
        rows.push(`${p.marker}${gas} <b>${(+p.value).toFixed(2)}</b>`);
      }
      return `${day}<br/>${rows.join("<br/>")}`;
    },
  },
  // 图例:仅列 7 个气体的「真实」系列(预测系列同色虚线,标题已注明真/预/预测区),
  // 避免 14 项盖图;底部横排滚动。
  legend: {
    data: GAS_VIZ.map((g) => `${g.sym}(真)`),
    formatter: (n) => n.replace("(真)", ""), // 图例去「(真)」后缀,只显气体名
    textStyle: { color: "#9ca3af", fontSize: 9 },
    bottom: 0,
    type: "scroll",
    itemWidth: 12,
    itemHeight: 6,
  },
  // 上留白容纳双 y 轴顶部数字(不被标题压);下留白让 x 轴日期与图例分两行不重叠
  grid: { top: 34, bottom: 50, left: 40, right: 60 },
  xAxis: {
    type: "category",
    data: predictXAxis.value,
    ...AXIS,
    axisLabel: { ...AXIS.axisLabel, interval: 3 },
  },
  yAxis: [
    {
      type: "value",
      name: "μL/L",
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
}));

// === Agent 5 步流水线 ===
// === ③ Agent 流水线:接 /agent/run 真实预跑轨迹(模块6,D-041 已完成)===
// Agent ReAct 4 工具步(取数→检测→预测→规则)+ 第5步生成通知(notice 字段)。
// 守边界:只显步骤名 + 完成态,不显 notice 细节文本(notice 已过黑名单校验)。
const AGENT_STEP_NAMES = ["获取数据", "异常检测", "趋势预测", "规则判级", "生成通知"];
const agentSteps = computed(() => {
  const r = agentRun.value;
  // 未预跑:5 步占位(灰)
  if (!r || !r.steps) {
    return AGENT_STEP_NAMES.map((title) => ({ title, cls: "pending" }));
  }
  // 真实 4 工具步按 status 着色 + 第5步「生成通知」据 notice 是否产出
  const toolSteps = r.steps.map((s, i) => ({
    title: AGENT_STEP_NAMES[i] || s.tool,
    cls: s.status === "success" ? "done" : "failed",
  }));
  toolSteps.push({
    title: "生成通知",
    cls: r.notice ? "done" : "pending",
  });
  return toolSteps;
});

// === 关键指标聚焦（7 气体可切换）===
// === ② 7 气体指标卡:接 latest.gases 当前值 + forecast 预测末日(D+n)===
// 阈值口径同 AnalysisView / 后端 ATTENTION_VALUES:仅 H₂/C₂H₂/总烃有国标注意值
// (DL/T 722-2014 表3,220kV 及以下);CO/CO₂/单个烃类不设绝对阈值(D-044),
// threshold=null,卡片显「无注意值」不画进度条。预测源 ARIMA(同预测大图)。
const METRIC_DEFS = [
  { key: "c2h2", sym: "C₂H₂", threshold: 5 },
  { key: "h2", sym: "H₂", threshold: 150 },
  { key: "ch4", sym: "CH₄", threshold: null },
  { key: "c2h6", sym: "C₂H₆", threshold: null },
  { key: "c2h4", sym: "C₂H₄", threshold: null },
  { key: "co", sym: "CO", threshold: null },
  { key: "co2", sym: "CO₂", threshold: null },
];

const metricGases = computed(() => {
  const g = latest.value ? latest.value.gases : null;
  const fcLast = forecast.value
    ? forecast.value.forecast[forecast.value.forecast.length - 1]
    : null;
  return METRIC_DEFS.map((m) => {
    const value = g && g[m.key] != null ? +g[m.key].toFixed(2) : null;
    const predict = fcLast && fcLast[m.key] != null ? +fcLast[m.key].toFixed(2) : null;
    // 超注意值标红(仅有阈值的气体);预测超标给提示
    const over = m.threshold != null && value != null && value > m.threshold;
    const predOver = m.threshold != null && predict != null && predict > m.threshold;
    return {
      sym: m.sym,
      value,
      threshold: m.threshold,
      valueClass: over ? "text-red-400" : "text-cyan-300",
      predict,
      predictClass: predOver ? "text-red-300" : "text-gray-300",
      predictHint: predOver ? "(预测超注意值)" : "",
    };
  });
});

const selectedMetric = ref("C₂H₂");
const currentMetric = computed(
  () =>
    metricGases.value.find((g) => g.sym === selectedMetric.value) ||
    metricGases.value[0],
);

// === ③ 活跃预警列表:接 /warning/backtest 真实触发工单(最近 12 条)===
// 数据源同 AlertsView(scripts/backtest.py 落盘);取最近触发日,显真实等级 +
// 日期 + 首条触发明细(message 已是 μL/L 真值,守边界 D-008 无故障类型)。
const LEVEL_VIZ = {
  red: { label: "🔴 红", tag: "tag-red", border: "border-red-500" },
  orange: { label: "🟠 橙", tag: "tag-org", border: "border-orange-500" },
  yellow: { label: "🟡 黄", tag: "tag-yel", border: "border-yellow-500" },
  blue: { label: "🔵 蓝", tag: "tag-blu", border: "border-blue-500" },
};

const allAlerts = computed(() => {
  const src = backtest.value ? backtest.value.alerts : [];
  // 按日期倒序取最近 12 条触发工单
  return [...src]
    .sort((a, b) => (a.date < b.date ? 1 : -1))
    .slice(0, 12)
    .map((a) => {
      const viz = LEVEL_VIZ[a.level] || LEVEL_VIZ.blue;
      const firstMsg =
        a.messages && a.messages.length ? a.messages[0].message : "";
      return {
        level: viz.label,
        tag: viz.tag,
        border: viz.border,
        time: a.date,
        msg: firstMsg,
      };
    });
});

// 滚动展示:列表非空才复制一份接成无缝滚动
const marqueeAlerts = computed(() =>
  allAlerts.value.length ? [...allAlerts.value, ...allAlerts.value] : [],
);
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
  padding: 6px 2px;
  gap: 4px;
}
.agent-step {
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;
}
/* num 圆基础态(中性灰,默认)*/
.agent-step-num {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 10px;
  flex-shrink: 0;
  background: rgba(75, 85, 99, 0.35);
  color: #9ca3af;
  border: 1.5px solid rgba(107, 114, 128, 0.6);
  position: relative;
  z-index: 2;
}
/* ✅ 通过 done:绿 */
.agent-step.done .agent-step-num {
  background: rgba(16, 185, 129, 0.15);
  color: #6ee7b7;
  border-color: #10b981;
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.35);
}
/* ❌ 异常 failed:红 */
.agent-step.failed .agent-step-num {
  background: rgba(239, 68, 68, 0.15);
  color: #fca5a5;
  border-color: #ef4444;
  box-shadow: 0 0 6px rgba(239, 68, 68, 0.4);
}
/* ⏳ 默认/未执行 pending:灰(显式声明,同基础)*/
.agent-step.pending .agent-step-num {
  background: rgba(75, 85, 99, 0.35);
  color: #9ca3af;
  border-color: rgba(107, 114, 128, 0.6);
  box-shadow: none;
}
.agent-step-title {
  font-size: 12px;
  color: #d1d5db;
  font-weight: 500;
}
.agent-step.failed .agent-step-title {
  color: #fca5a5;
}
.agent-step.pending .agent-step-title {
  color: #6b7280;
}
/* 连接线:默认灰,done 绿 / failed 红;接到下一圆圈 */
.agent-step-connector {
  position: absolute;
  left: 9px;
  top: 20px;
  bottom: -12px;
  width: 2px;
  background: rgba(75, 85, 99, 0.4);
  z-index: 1;
}
.agent-step.done .agent-step-connector {
  background: linear-gradient(180deg, #10b981 0%, rgba(16, 185, 129, 0.4) 100%);
}
.agent-step.failed .agent-step-connector {
  background: rgba(239, 68, 68, 0.5);
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
  flex-wrap: wrap;
  justify-content: flex-end;
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
