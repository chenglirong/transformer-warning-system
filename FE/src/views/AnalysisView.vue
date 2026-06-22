<template>
  <div class="h-screen flex flex-col">
    <AppHeader
      title="三 层 数 据 体 系（监 测 对 象）"
      icon="mdi:layers-triple"
    >
      <template #actions>
        <div class="flex items-center gap-2">
          <span class="text-[11px] text-gray-400">查看日期</span>
          <el-date-picker
            v-model="pickedDate"
            type="date"
            size="small"
            value-format="YYYY-MM-DD"
            :clearable="false"
            :disabled-date="disabledDate"
            :cell-class-name="cellClass"
            placeholder="选择日期"
            class="analysis-date-picker"
            popper-class="analysis-picker-popper"
          />
          <span
            v-if="snapshot"
            class="text-[11px] px-2 py-0.5 rounded border"
            :class="snapshot.is_abnormal
              ? 'text-red-300 border-red-500/40 bg-red-500/10'
              : 'text-green-300 border-green-500/40 bg-green-500/10'"
          >
            {{ snapshot.is_abnormal ? '异常日' : '正常日' }}
          </span>
        </div>
      </template>
    </AppHeader>

    <main class="flex-1 flex flex-col gap-2 p-3 overflow-hidden" style="min-height: 0">
      <!-- Tier 1: DGA 7 气体（直接检测）-->
      <section class="tier" style="flex: 1.4">
        <div class="tier-header tier-1">
          <div class="tier-label">
            <span class="tier-num">第 1 层</span>
            <span class="tier-title">DGA 七气体（直接检测）</span>
            <span class="tier-desc">核心地位 · LSTM 预测目标 + 预警核心依据</span>
          </div>
          <span class="text-[10px] text-gray-400">
            数据采样：每日 1 次 · 当前值取最新一日（{{ latestDate }}）
          </span>
        </div>
        <div class="grid grid-cols-7 gap-2 flex-1" style="min-height: 0">
          <div
            v-for="g in gases"
            :key="g.sym"
            class="gas-card"
            :class="g.cls"
          >
            <div class="flex items-baseline justify-between">
              <span class="text-xs font-bold text-gray-200">{{ g.sym }}</span>
              <iconify-icon
                v-if="g.alert"
                class="text-sm pulse"
                :class="g.alertClass"
                icon="mdi:alert"
              ></iconify-icon>
            </div>
            <p class="text-[10px] text-gray-500">{{ g.zh }}</p>
            <p class="text-2xl font-bold mt-1" :class="g.valueClass">
              {{ g.value }}<span class="text-[10px] ml-0.5 text-gray-500">μL/L</span>
            </p>
            <div class="flex items-center justify-between text-[10px]">
              <span class="text-gray-500">{{ g.thresholdLabel }}</span>
              <span :class="g.trendClass">{{ g.trend }}</span>
            </div>
            <div class="flex-1 mt-1" style="min-height: 0">
              <EChart :option="g.sparkOption" />
            </div>
          </div>
        </div>
      </section>

      <!-- Tier 2: 衍生指标（特征工程） -->
      <section class="tier" style="flex: 1.2">
        <div class="tier-header tier-2">
          <div class="tier-label">
            <span class="tier-num">第 2 层</span>
            <span class="tier-title">衍生指标（特征工程计算）</span>
            <span class="tier-desc">从 DGA 计算得到 · 喂入预警规则</span>
          </div>
          <span class="text-[10px] text-gray-400">
            产气速率、气体比值是预警关键 — 涨得快比当前值高更危险
          </span>
        </div>
        <div class="grid grid-cols-12 gap-2 flex-1" style="min-height: 0">
          <!-- 总烃 -->
          <div class="col-span-3 flex flex-col gap-2 overflow-hidden">
            <div class="derived-card highlight flex-1">
              <p class="text-[11px] text-gray-400">总烃 = ΣCH₄+C₂H₄+C₂H₆+C₂H₂</p>
              <p class="text-3xl font-bold text-cyan-300 mt-1">
                {{ totalHC.value }}<span class="text-xs ml-1 text-gray-400">μL/L</span>
              </p>
              <p class="text-[10px]" :class="totalHC.rateClass">
                7d {{ totalHC.rate }} · 注意值 150
              </p>
            </div>
          </div>

          <!-- 气体特征比值（中性衍生数值，非 IEC 诊断编码）-->
          <div class="col-span-4 flex flex-col gap-2 overflow-hidden">
            <div class="derived-card flex-1 flex flex-col">
              <p class="text-[11px] text-gray-400 mb-1.5">
                气体特征比值(衍生指标)
              </p>
              <div class="grid grid-cols-3 gap-1.5 text-center">
                <div
                  v-for="r in ratios"
                  :key="r.name"
                  class="bg-gray-800/60 rounded p-1.5 border border-gray-700/40"
                >
                  <p class="text-[9px] text-gray-500">{{ r.name }}</p>
                  <p class="text-base font-bold text-yellow-400">{{ r.value }}</p>
                </div>
              </div>
              <p class="mt-auto text-[9px] text-gray-500 leading-tight">
                比值为特征工程衍生数值,供模型/规则使用;具体故障判别属诊断范畴,不在本预警系统输出
              </p>
            </div>
          </div>

          <!-- 7 气体 72h 产气速率 -->
          <div class="col-span-5 derived-card flex flex-col overflow-hidden">
            <p class="text-[11px] text-gray-400 mb-1">
              7 气体 72h 产气速率（%）· 红色 ≥ 20% 触发预警
            </p>
            <div class="flex-1" style="min-height: 0">
              <EChart :option="rateOption" />
            </div>
          </div>
        </div>
      </section>

      <!-- Tier 3: 运行工况（辅助判断） -->
      <section class="tier" style="flex: 1">
        <div class="tier-header tier-3">
          <div class="tier-label">
            <span class="tier-num">第 3 层</span>
            <span class="tier-title">运行工况（辅助判断）</span>
            <span class="tier-desc">辅助地位 · 为规则引擎提供上下文,不直接参与 LSTM 预测</span>
          </div>
          <span class="text-[10px] text-yellow-300/70">
            <iconify-icon icon="mdi:information"></iconify-icon>
            示例规则：油温 &gt; 80 AND 负载 &gt; 1.0 → 橙色预警
          </span>
        </div>
        <div class="grid grid-cols-4 gap-2 flex-1" style="min-height: 0">
          <div
            v-for="c in conditions"
            :key="c.label"
            class="condition-card"
            :class="c.cls"
          >
            <div class="flex items-center justify-between">
              <span class="text-[11px] text-gray-400">{{ c.label }}</span>
              <iconify-icon
                v-if="c.alert"
                class="text-xs"
                :class="c.alertClass"
                icon="mdi:alert-circle"
              ></iconify-icon>
            </div>
            <div class="flex items-baseline gap-1 mt-1">
              <span class="text-2xl font-bold" :class="c.valueClass">
                {{ c.value }}
              </span>
              <span class="text-[11px] text-gray-500">{{ c.unit }}</span>
              <span class="text-[10px] text-gray-500 ml-auto">
                {{ c.threshold }}
              </span>
            </div>
            <div class="flex-1" style="min-height: 0">
              <EChart :option="c.option" />
            </div>
          </div>
        </div>
      </section>
    </main>

    <AppFooter />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import AppHeader from "@/components/AppHeader.vue";
import AppFooter from "@/components/AppFooter.vue";
import EChart from "@/components/EChart.vue";
import { AXIS, TT } from "@/utils/chartDefaults";
import { getSnapshot, getTimeseries, getDates } from "@/service/api";

const TRANSFORMER_ID = 1; // 单设备方案

// 三层数据据实接真:snapshot(选中日的当前值 + 第2层 features)
// + timeseries(截止选中日的近 30 天曲线,保证数字与曲线同窗口)
const snapshot = ref(null);
const series = ref([]); // 截止选中日的近 30 天逐日记录

// 日期选择器:可回看任意一天的三层数据(默认最新日);异常日历标红点
const pickedDate = ref(null); // "YYYY-MM-DD"
const dateRange = ref({ start: null, end: null });
const abnormalSet = ref(new Set()); // 异常日集合(二分类,无故障类型)

const latestDate = computed(() => snapshot.value?.date ?? "—");

// 本地日期 → YYYY-MM-DD(避开 toISOString 的 UTC 时区偏移)
function toISO(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

// 日历:范围外禁选
const disabledDate = (d) => {
  if (!dateRange.value.start || !dateRange.value.end) return false;
  const iso = toISO(d);
  return iso < dateRange.value.start || iso > dateRange.value.end;
};
// 日历:异常日单元格加红点 class(入参为原生 Date,见 verify)
const cellClass = (d) =>
  d instanceof Date && abnormalSet.value.has(toISO(d)) ? "abnormal-cell" : "";

async function loadSnapshot(on) {
  try {
    snapshot.value = await getSnapshot(TRANSFORMER_ID, on);
  } catch (e) {
    console.warn("[AnalysisView] snapshot 拉取失败,三层显示占位", e);
    return;
  }
  try {
    // 曲线截止到选中日(end),与当前值同窗口;首次 on 为空时取最新日
    const ts = await getTimeseries(TRANSFORMER_ID, 30, snapshot.value?.date);
    series.value = ts?.series ?? [];
  } catch (e) {
    console.warn("[AnalysisView] timeseries 拉取失败,曲线显示空", e);
  }
}

onMounted(async () => {
  // 先拉日期表(范围 + 异常标记),再默认加载最新日
  try {
    const dd = await getDates(TRANSFORMER_ID);
    dateRange.value = { start: dd.start_date, end: dd.end_date };
    abnormalSet.value = new Set(
      (dd.days ?? []).filter((x) => x.is_abnormal).map((x) => x.date)
    );
  } catch (e) {
    console.warn("[AnalysisView] dates 拉取失败,日期选择器降级", e);
  }
  await loadSnapshot(); // 默认最新日
  pickedDate.value = snapshot.value?.date ?? null;
});

// 切日期 → 重载三层(跳过与当前一致的回填)
watch(pickedDate, (v) => {
  if (v && v !== snapshot.value?.date) loadSnapshot(v);
});

// ============ 第 1 层:DGA 七气体 ============
// 阈值(与后端 threshold.ATTENTION_VALUES 同口径):仅 H₂/C₂H₂/总烃为国标 DL/T 722-2014
// 表3 注意值(220kV 及以下)。CO/CO₂ 表3 未设绝对注意值(D-044),固体绝缘走 §10.2.3.1
// 的 CO₂/CO 比值法,故不在此标单气体阈值线(attn=null,同烃类分量)。
const GAS_META = [
  { key: "h2", sym: "H₂", zh: "氢气", color: "#10b981", attn: 150 },
  { key: "ch4", sym: "CH₄", zh: "甲烷", color: "#06b6d4", attn: null },
  { key: "c2h6", sym: "C₂H₆", zh: "乙烷", color: "#8b5cf6", attn: null },
  { key: "c2h4", sym: "C₂H₄", zh: "乙烯", color: "#f59e0b", attn: null },
  { key: "c2h2", sym: "C₂H₂", zh: "乙炔", color: "#ef4444", attn: 5 },
  { key: "co", sym: "CO", zh: "一氧化碳", color: "#a3e635", attn: null },
  { key: "co2", sym: "CO₂", zh: "二氧化碳", color: "#f472b6", attn: null },
];

const buildSpark = (data, color, threshold) => ({
  tooltip: { ...TT, trigger: "axis" },
  grid: { top: 4, bottom: 16, left: 4, right: 4 },
  xAxis: {
    type: "category",
    data: data.map((_, i) => `D-${data.length - 1 - i}`),
    show: false,
  },
  yAxis: { type: "value", show: false, max: threshold ? threshold : null },
  series: [
    {
      type: "line",
      smooth: true,
      data,
      symbol: "none",
      lineStyle: { color, width: 1.5 },
      areaStyle: {
        color: {
          type: "linear", x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: color + "55" },
            { offset: 1, color: color + "00" },
          ],
        },
      },
      ...(threshold
        ? {
            markLine: {
              symbol: "none",
              lineStyle: { color: "#ef4444", type: "dashed", width: 1 },
              label: { show: false },
              data: [{ yAxis: threshold }],
            },
          }
        : {}),
    },
  ],
});

const gases = computed(() =>
  GAS_META.map((m) => {
    const g = snapshot.value?.gases;
    const hist = series.value.map((d) => d[m.key]).filter((v) => v != null);
    const cur = g?.[m.key];
    // 近 7 天涨幅:用 series 头尾(无足够历史则不显)
    let trend = "";
    let trendClass = "text-gray-500";
    if (hist.length >= 8) {
      const prev = hist[hist.length - 8];
      const last = hist[hist.length - 1];
      if (prev > 0) {
        const pct = ((last - prev) / prev) * 100;
        const s = pct >= 0 ? "↑" : "↓";
        trend = `7d ${s} ${Math.abs(pct).toFixed(0)}%`;
        trendClass =
          pct >= 20 ? "text-red-400" : pct >= 8 ? "text-orange-400"
            : pct >= 0 ? "text-yellow-400" : "text-green-400";
      }
    }
    // 超国标注意值则标警(仅有注意值的气体)
    const over = m.attn != null && cur != null && cur > m.attn;
    return {
      sym: m.sym,
      zh: m.zh,
      value: cur != null ? cur.toFixed(cur < 10 ? 2 : 1) : "—",
      thresholdLabel: m.attn != null ? `/ ${m.attn}${over ? " ⚠" : ""}` : "无注意值",
      trend,
      trendClass,
      valueClass: over ? "text-red-400" : "text-gray-100",
      cls: over ? "danger" : "",
      alert: over,
      alertClass: "text-red-400",
      sparkOption: buildSpark(hist, m.color, m.attn),
    };
  })
);

// ============ 第 2 层:衍生指标(特征工程) ============
const fmtRate = (v) => {
  if (v == null) return { rate: "—", rateClass: "text-gray-500" };
  const s = v >= 0 ? "↑" : "↓";
  const cls =
    v >= 20 ? "text-red-400" : v >= 8 ? "text-orange-400"
      : v >= 0 ? "text-yellow-400" : "text-green-400";
  return { rate: `${s} ${Math.abs(v).toFixed(1)}%`, rateClass: cls };
};

const totalHC = computed(() => {
  const f = snapshot.value?.features;
  const r = fmtRate(f?.total_hydrocarbon_rate);
  return {
    value: f?.total_hydrocarbon != null ? f.total_hydrocarbon.toFixed(1) : "—",
    rate: r.rate,
    rateClass: r.rateClass,
  };
});

// 三比值:仅数值(中性衍生指标),不含 IEC 编码/故障类型(守系统边界 docs/04)
const ratios = computed(() => {
  const r = snapshot.value?.features?.ratios;
  const fmt = (v) => (v != null ? v.toFixed(2) : "—");
  return [
    { name: "C₂H₂/C₂H₄", value: fmt(r?.c2h2_c2h4) },
    { name: "CH₄/H₂", value: fmt(r?.ch4_h2) },
    { name: "C₂H₄/C₂H₆", value: fmt(r?.c2h4_c2h6) },
  ];
});

// 7 气体 72h 产气速率(%),接 features.gas_rate_pct 真值
const RATE_ORDER = [
  { key: "co2", sym: "CO₂" }, { key: "co", sym: "CO" },
  { key: "c2h2", sym: "C₂H₂" }, { key: "c2h4", sym: "C₂H₄" },
  { key: "c2h6", sym: "C₂H₆" }, { key: "ch4", sym: "CH₄" },
  { key: "h2", sym: "H₂" },
];
const rateOption = computed(() => {
  const gr = snapshot.value?.features?.gas_rate_pct ?? {};
  const cats = RATE_ORDER.map((r) => r.sym);
  const vals = RATE_ORDER.map((r) => {
    const v = gr[r.key];
    return v == null ? 0 : +v.toFixed(1);
  });
  return {
    tooltip: { trigger: "axis", ...TT },
    grid: { top: 20, bottom: 18, left: 40, right: 30 },
    xAxis: {
      type: "value",
      ...AXIS,
      axisLabel: { ...AXIS.axisLabel, fontSize: 9, formatter: "{value}%" },
    },
    yAxis: {
      type: "category",
      data: cats,
      ...AXIS,
      axisLabel: { ...AXIS.axisLabel, fontSize: 10 },
    },
    series: [
      {
        type: "bar",
        data: vals,
        itemStyle: {
          color: (p) =>
            p.value >= 20 ? "#ef4444" : p.value >= 15 ? "#f59e0b"
              : p.value >= 0 ? "#10b981" : "#3b82f6",
          borderRadius: [0, 4, 4, 0],
        },
        label: {
          show: true,
          position: "right",
          color: "#e5e7eb",
          fontSize: 9,
          formatter: "{c}%",
        },
        barWidth: 12,
        markLine: {
          symbol: "none",
          data: [
            {
              xAxis: 20,
              lineStyle: { color: "#ef4444", type: "dashed" },
              label: {
                formatter: "20% 预警",
                color: "#fca5a5",
                fontSize: 9,
                position: "end",
                distance: [0, 2],
                padding: [1, 3],
                backgroundColor: "rgba(17,24,39,0.85)",
                borderRadius: 2,
              },
            },
          ],
        },
      },
    ],
  };
});

// ============ 第 3 层:运行工况 ============
const buildCondTrend = (data, color, threshold) => ({
  tooltip: { ...TT, trigger: "axis" },
  grid: { top: 4, bottom: 16, left: 4, right: 4 },
  xAxis: { type: "category", data: data.map((_, i) => i), show: false },
  yAxis: { type: "value", show: false, max: threshold ? threshold * 1.1 : null },
  series: [
    {
      type: "line",
      smooth: true,
      data,
      symbol: "none",
      lineStyle: { color, width: 1.5 },
      areaStyle: {
        color: {
          type: "linear", x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: color + "55" },
            { offset: 1, color: color + "00" },
          ],
        },
      },
      ...(threshold
        ? {
            markLine: {
              symbol: "none",
              lineStyle: { color: "#ef4444", type: "dashed", width: 1 },
              label: { show: false },
              data: [{ yAxis: threshold }],
            },
          }
        : {}),
    },
  ],
});

// 工况口径:油温注意 95℃、负载额定 250A、环温参考 40℃(承 Dashboard/合成器口径)
const conditions = computed(() => {
  const c = snapshot.value?.conditions;
  const oilHist = series.value.map((d) => d.oil_temp).filter((v) => v != null);
  const loadHist = series.value.map((d) => d.load_current).filter((v) => v != null);
  const ambHist = series.value.map((d) => d.ambient_temp).filter((v) => v != null);
  const fmt = (v, d = 0) => (v != null ? v.toFixed(d) : "—");
  const oil = c?.oil_temp;
  const load = c?.load_current;
  const amb = c?.ambient_temp;
  return [
    {
      label: "顶层油温",
      value: fmt(oil, 1),
      unit: "℃",
      threshold: "/ 95",
      valueClass: oil != null && oil > 95 ? "text-red-400" : "text-green-400",
      cls: oil != null && oil > 95 ? "warn" : "ok",
      alert: oil != null && oil > 95,
      alertClass: "text-red-400",
      option: buildCondTrend(oilHist, "#10b981", 95),
    },
    {
      label: "温升速率(油温日变化)",
      value: oilHist.length >= 2 ? fmt(oilHist[oilHist.length - 1] - oilHist[oilHist.length - 2], 1) : "—",
      unit: "℃/d",
      threshold: "参考",
      valueClass: "text-green-400",
      cls: "ok",
      alert: false,
      option: buildCondTrend(
        oilHist.slice(1).map((v, i) => +(v - oilHist[i]).toFixed(2)),
        "#10b981",
        null
      ),
    },
    {
      label: "负载电流",
      value: fmt(load, 0),
      unit: "A",
      threshold: "/ 250",
      valueClass: load != null && load > 250 ? "text-orange-400" : "text-green-400",
      cls: load != null && load > 250 ? "warn" : "ok",
      alert: load != null && load > 250,
      alertClass: "text-orange-400",
      option: buildCondTrend(loadHist, "#f97316", 250),
    },
    {
      label: "环境温度",
      value: fmt(amb, 1),
      unit: "℃",
      threshold: "/ 40",
      valueClass: amb != null && amb > 40 ? "text-yellow-400" : "text-green-400",
      cls: amb != null && amb > 40 ? "warn" : "ok",
      alert: amb != null && amb > 40,
      alertClass: "text-yellow-400",
      option: buildCondTrend(ambHist, "#eab308", 40),
    },
  ];
});
</script>

<style scoped>
.tier {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 0;
}

.tier-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-radius: 4px;
  border-left: 3px solid;
  flex-shrink: 0;
}
.tier-1 {
  background: linear-gradient(90deg, rgba(6, 182, 212, 0.15), rgba(6, 182, 212, 0));
  border-color: #06b6d4;
}
.tier-2 {
  background: linear-gradient(90deg, rgba(168, 85, 247, 0.15), rgba(168, 85, 247, 0));
  border-color: #a855f7;
}
.tier-3 {
  background: linear-gradient(90deg, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0));
  border-color: #f59e0b;
}
.tier-label {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.tier-num {
  font-size: 10px;
  color: #9ca3af;
  border: 1px solid rgba(156, 163, 175, 0.4);
  padding: 1px 6px;
  border-radius: 3px;
}
.tier-1 .tier-num {
  color: #67e8f9;
  border-color: rgba(103, 232, 249, 0.4);
}
.tier-2 .tier-num {
  color: #d8b4fe;
  border-color: rgba(216, 180, 254, 0.4);
}
.tier-3 .tier-num {
  color: #fcd34d;
  border-color: rgba(252, 211, 77, 0.4);
}
.tier-title {
  font-size: 13px;
  font-weight: 700;
  color: #e5e7eb;
}
.tier-desc {
  font-size: 11px;
  color: #6b7280;
}

.gas-card {
  background: rgba(17, 24, 39, 0.72);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(75, 85, 99, 0.4);
  border-radius: 6px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.gas-card.warn {
  border-color: rgba(245, 158, 11, 0.5);
  box-shadow: inset 0 0 12px rgba(245, 158, 11, 0.08);
}
.gas-card.danger {
  border-color: rgba(239, 68, 68, 0.55);
  box-shadow: inset 0 0 14px rgba(239, 68, 68, 0.12);
}

.derived-card {
  background: rgba(17, 24, 39, 0.72);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(75, 85, 99, 0.4);
  border-radius: 6px;
  padding: 10px;
  min-height: 0;
}
.derived-card.highlight {
  border-color: rgba(6, 182, 212, 0.4);
  box-shadow: inset 0 0 14px rgba(6, 182, 212, 0.08);
}

.condition-card {
  background: rgba(17, 24, 39, 0.72);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(75, 85, 99, 0.4);
  border-radius: 6px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.condition-card.ok {
  border-color: rgba(16, 185, 129, 0.35);
}
.condition-card.warn {
  border-color: rgba(245, 158, 11, 0.5);
  box-shadow: inset 0 0 12px rgba(245, 158, 11, 0.08);
}
</style>
