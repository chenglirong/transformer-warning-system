<template>
  <div class="h-screen flex flex-col">
    <AppHeader
      title="三 层 指 标 体 系（数 据 看 板）"
      icon="mdi:layers-triple"
      subtitle="DGA 七气体 · 衍生指标（特征工程） · 工况辅助"
    />

    <main class="flex-1 flex flex-col gap-2 p-3 overflow-hidden" style="min-height: 0">
      <!-- Tier 1: DGA 7 气体（直接检测）-->
      <section class="tier" style="flex: 1.4">
        <div class="tier-header tier-1">
          <div class="tier-label">
            <span class="tier-num">第 1 层</span>
            <span class="tier-title">DGA 七气体（直接检测）</span>
            <span class="tier-desc">LSTM 预测目标 · 预警核心依据</span>
          </div>
          <span class="text-[10px] text-gray-400">
            数据采样：每日 1 次 · 来源 IEC TC 10 公开数据集
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
              {{ g.value }}<span class="text-[10px] ml-0.5 text-gray-500">ppm</span>
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
            <span class="tier-title">衍生指标（特征工程）</span>
            <span class="tier-desc">从 DGA 计算得到 · 喂入预警规则</span>
          </div>
          <span class="text-[10px] text-gray-400">
            产气速率、气体比值是预警关键 — 涨得快比当前值高更危险
          </span>
        </div>
        <div class="grid grid-cols-12 gap-2 flex-1" style="min-height: 0">
          <!-- 总烃 + 关键比值 -->
          <div class="col-span-3 flex flex-col gap-2 overflow-hidden">
            <div class="derived-card highlight">
              <p class="text-[11px] text-gray-400">总烃 = ΣCH₄+C₂H₄+C₂H₆+C₂H₂</p>
              <p class="text-3xl font-bold text-cyan-300 mt-1">
                129.3<span class="text-xs ml-1 text-gray-400">ppm</span>
              </p>
              <p class="text-[10px] text-gray-500">7d ↑ 18% · 阈值 150</p>
            </div>
            <div class="derived-card">
              <p class="text-[11px] text-gray-400">CO₂ / CO 比值</p>
              <p class="text-2xl font-bold text-green-300 mt-1">5.9</p>
              <p class="text-[10px] text-gray-500">固体绝缘正常（&gt;3）</p>
            </div>
          </div>

          <!-- 三比值法编码 + 判定 -->
          <div class="col-span-4 flex flex-col gap-2 overflow-hidden">
            <div class="derived-card flex-1 flex flex-col">
              <p class="text-[11px] text-gray-400 mb-1.5">
                IEC 三比值法 · 编码 / 判定
              </p>
              <div class="grid grid-cols-3 gap-1.5 text-center">
                <div
                  v-for="r in ratios"
                  :key="r.name"
                  class="bg-gray-800/60 rounded p-1.5 border border-gray-700/40"
                >
                  <p class="text-[9px] text-gray-500">{{ r.name }}</p>
                  <p class="text-base font-bold text-yellow-400">{{ r.value }}</p>
                  <p class="text-[10px] text-gray-400">编码 {{ r.code }}</p>
                </div>
              </div>
              <div
                class="mt-1.5 px-2 py-1.5 bg-orange-500/10 border border-orange-500/40 rounded flex items-center justify-between"
              >
                <span class="text-[10px] text-gray-300">码集</span>
                <span class="text-[11px] text-orange-300 font-bold">
                  021 → 低温过热 (&lt;300℃)
                </span>
              </div>
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
            <span class="tier-desc">为规则引擎提供上下文 · 不参与 LSTM 预测</span>
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
import AppHeader from "@/components/AppHeader.vue";
import AppFooter from "@/components/AppFooter.vue";
import EChart from "@/components/EChart.vue";
import { AXIS, TT } from "@/utils/chartDefaults";

const buildSpark = (data, color, threshold) => ({
  tooltip: { ...TT, trigger: "axis" },
  grid: { top: 4, bottom: 16, left: 4, right: 4 },
  xAxis: {
    type: "category",
    data: Array.from({ length: 30 }, (_, i) => `D-${29 - i}`),
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
          type: "linear",
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
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

const genHist = (start, end, wave = 0.05) =>
  Array.from({ length: 30 }, (_, i) => {
    const t = i / 29;
    const v = start + (end - start) * t;
    return +(
      v *
      (1 + (Math.sin(i * 0.7) + (Math.random() - 0.5) * 0.5) * wave)
    ).toFixed(2);
  });

const gases = [
  {
    sym: "H₂",
    zh: "氢气",
    value: "42.5",
    thresholdLabel: "/ 150",
    trend: "↑ 5%",
    trendClass: "text-yellow-400",
    valueClass: "text-green-400",
    cls: "",
    alert: false,
    sparkOption: buildSpark(genHist(25, 42.5), "#10b981"),
  },
  {
    sym: "CH₄",
    zh: "甲烷",
    value: "58.2",
    thresholdLabel: "/ 100",
    trend: "↑ 38%",
    trendClass: "text-orange-400",
    valueClass: "text-cyan-400",
    cls: "",
    alert: false,
    sparkOption: buildSpark(genHist(35, 58.2), "#06b6d4"),
  },
  {
    sym: "C₂H₆",
    zh: "乙烷",
    value: "22.8",
    thresholdLabel: "/ 50",
    trend: "↑ 27%",
    trendClass: "text-yellow-400",
    valueClass: "text-purple-400",
    cls: "",
    alert: false,
    sparkOption: buildSpark(genHist(15, 22.8), "#8b5cf6"),
  },
  {
    sym: "C₂H₄",
    zh: "乙烯（过热）",
    value: "45.1",
    thresholdLabel: "/ 100 ⚠",
    trend: "72h ↑ 23%",
    trendClass: "text-orange-400",
    valueClass: "text-yellow-400",
    cls: "warn",
    alert: false,
    sparkOption: buildSpark(genHist(22, 45.1), "#f59e0b"),
  },
  {
    sym: "C₂H₂",
    zh: "乙炔（放电）",
    value: "3.24",
    thresholdLabel: "/ 5 ⚠",
    trend: "↑ 18%",
    trendClass: "text-red-400",
    valueClass: "text-red-400",
    cls: "danger",
    alert: true,
    alertClass: "text-red-400",
    sparkOption: buildSpark(
      [
        0.8, 0.9, 1.0, 1.1, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0,
        2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 3.0, 3.05, 3.1, 3.15, 3.2,
        3.22, 3.24,
      ],
      "#ef4444",
      5
    ),
  },
  {
    sym: "CO",
    zh: "一氧化碳",
    value: "312",
    thresholdLabel: "绝缘老化",
    trend: "↑ 3%",
    trendClass: "text-green-400",
    valueClass: "text-lime-400",
    cls: "",
    alert: false,
    sparkOption: buildSpark(genHist(260, 312), "#a3e635"),
  },
  {
    sym: "CO₂",
    zh: "二氧化碳",
    value: "1840",
    thresholdLabel: "/ 2000",
    trend: "↑ 2%",
    trendClass: "text-yellow-400",
    valueClass: "text-pink-400",
    cls: "",
    alert: false,
    sparkOption: buildSpark(genHist(1500, 1840), "#f472b6"),
  },
];

const ratios = [
  { name: "C₂H₂/C₂H₄", value: "0.072", code: 0 },
  { name: "CH₄/H₂", value: "1.37", code: 2 },
  { name: "C₂H₄/C₂H₆", value: "1.98", code: 1 },
];

const rateOption = {
  tooltip: { trigger: "axis", ...TT },
  grid: { top: 8, bottom: 18, left: 40, right: 18 },
  xAxis: {
    type: "value",
    ...AXIS,
    axisLabel: { ...AXIS.axisLabel, fontSize: 9, formatter: "{value}%" },
  },
  yAxis: {
    type: "category",
    data: ["CO₂", "CO", "C₂H₂", "C₂H₄", "C₂H₆", "CH₄", "H₂"],
    ...AXIS,
    axisLabel: { ...AXIS.axisLabel, fontSize: 10 },
  },
  series: [
    {
      type: "bar",
      data: [8, 12, 38, 23, 27, 18, 15],
      itemStyle: {
        color: (p) =>
          p.value >= 20 ? "#ef4444" : p.value >= 15 ? "#f59e0b" : "#10b981",
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
            },
          },
        ],
      },
    },
  ],
};

const buildCondTrend = (data, color, threshold) => ({
  tooltip: { ...TT, trigger: "axis" },
  grid: { top: 4, bottom: 16, left: 4, right: 4 },
  xAxis: {
    type: "category",
    data: ["00", "04", "08", "12", "16", "20", "24"],
    show: false,
  },
  yAxis: { type: "value", show: false, max: threshold * 1.1 },
  series: [
    {
      type: "line",
      smooth: true,
      data,
      symbol: "none",
      lineStyle: { color, width: 1.5 },
      areaStyle: {
        color: {
          type: "linear",
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: color + "55" },
            { offset: 1, color: color + "00" },
          ],
        },
      },
      markLine: {
        symbol: "none",
        lineStyle: { color: "#ef4444", type: "dashed", width: 1 },
        label: { show: false },
        data: [{ yAxis: threshold }],
      },
    },
  ],
});

const conditions = [
  {
    label: "顶层油温",
    value: "59",
    unit: "℃",
    threshold: "/ 95",
    valueClass: "text-green-400",
    cls: "ok",
    alert: false,
    option: buildCondTrend(
      [45, 42, 40, 42, 48, 52, 56, 58, 59, 58, 55, 50, 46].slice(0, 7),
      "#10b981",
      95
    ),
  },
  {
    label: "温升速率",
    value: "1.2",
    unit: "℃/h",
    threshold: "/ 3",
    valueClass: "text-green-400",
    cls: "ok",
    alert: false,
    option: buildCondTrend(
      [0.4, 0.3, 0.5, 0.7, 1.4, 1.2, 1.0],
      "#10b981",
      3
    ),
  },
  {
    label: "负载电流",
    value: "1.05",
    unit: "倍",
    threshold: "/ 1.1",
    valueClass: "text-orange-400",
    cls: "warn",
    alert: true,
    alertClass: "text-orange-400",
    option: buildCondTrend(
      [0.48, 0.44, 0.58, 0.79, 1.05, 0.87, 0.68],
      "#f97316",
      1.1
    ),
  },
  {
    label: "环境温度",
    value: "38",
    unit: "℃",
    threshold: "/ 40",
    valueClass: "text-yellow-400",
    cls: "warn",
    alert: true,
    alertClass: "text-yellow-400",
    option: buildCondTrend(
      [26, 24, 22, 24, 28, 31, 34, 36, 38].slice(0, 7),
      "#eab308",
      40
    ),
  },
];
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
  background: linear-gradient(
    90deg,
    rgba(6, 182, 212, 0.15),
    rgba(6, 182, 212, 0)
  );
  border-color: #06b6d4;
}
.tier-2 {
  background: linear-gradient(
    90deg,
    rgba(168, 85, 247, 0.15),
    rgba(168, 85, 247, 0)
  );
  border-color: #a855f7;
}
.tier-3 {
  background: linear-gradient(
    90deg,
    rgba(245, 158, 11, 0.15),
    rgba(245, 158, 11, 0)
  );
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
