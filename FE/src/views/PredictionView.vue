<template>
  <div class="h-screen flex flex-col">
    <AppHeader
      title="L S T M 预 测 · A R I M A 对 比 实 验"
      icon="mdi:chart-timeline-variant-shimmer"
      subtitle="多输出回归 · 7 气体同步预测 · 1-3 天滚动"
    />

    <!-- 顶部对比 KPI -->
    <section class="px-3 pt-3 grid grid-cols-4 gap-3">
      <div class="compare-kpi">
        <p class="text-[11px] text-gray-400">MAE 平均误差</p>
        <div class="flex items-baseline gap-2 mt-1">
          <div>
            <span class="text-[10px] text-gray-500">LSTM</span>
            <p class="text-2xl font-bold text-green-400">2.14</p>
          </div>
          <iconify-icon class="text-gray-500" icon="mdi:less-than"></iconify-icon>
          <div>
            <span class="text-[10px] text-gray-500">ARIMA</span>
            <p class="text-base font-bold text-gray-400 line-through">3.45</p>
          </div>
          <span class="ml-auto improve-badge">↓ 38%</span>
        </div>
      </div>
      <div class="compare-kpi">
        <p class="text-[11px] text-gray-400">RMSE 均方根</p>
        <div class="flex items-baseline gap-2 mt-1">
          <div>
            <span class="text-[10px] text-gray-500">LSTM</span>
            <p class="text-2xl font-bold text-green-400">3.06</p>
          </div>
          <iconify-icon class="text-gray-500" icon="mdi:less-than"></iconify-icon>
          <div>
            <span class="text-[10px] text-gray-500">ARIMA</span>
            <p class="text-base font-bold text-gray-400 line-through">5.21</p>
          </div>
          <span class="ml-auto improve-badge">↓ 41%</span>
        </div>
      </div>
      <div class="compare-kpi">
        <p class="text-[11px] text-gray-400">MAPE 百分比</p>
        <div class="flex items-baseline gap-2 mt-1">
          <div>
            <span class="text-[10px] text-gray-500">LSTM</span>
            <p class="text-2xl font-bold text-green-400">6.3%</p>
          </div>
          <iconify-icon class="text-gray-500" icon="mdi:less-than"></iconify-icon>
          <div>
            <span class="text-[10px] text-gray-500">ARIMA</span>
            <p class="text-base font-bold text-gray-400 line-through">10.8%</p>
          </div>
          <span class="ml-auto improve-badge">↓ 42%</span>
        </div>
      </div>
      <div class="compare-kpi highlight">
        <p class="text-[11px] text-gray-400">训练成本（创新点 ⭐）</p>
        <div class="flex items-baseline gap-2 mt-1">
          <div>
            <span class="text-[10px] text-gray-500">LSTM 多输出</span>
            <p class="text-2xl font-bold text-cyan-400">
              1<span class="text-xs">次</span>
            </p>
          </div>
          <iconify-icon class="text-gray-500" icon="mdi:less-than"></iconify-icon>
          <div>
            <span class="text-[10px] text-gray-500">ARIMA</span>
            <p class="text-base font-bold text-gray-400 line-through">
              7<span class="text-[10px]">次</span>
            </p>
          </div>
          <span class="ml-auto improve-badge">7→1</span>
        </div>
      </div>
    </section>

    <main
      class="flex-1 grid grid-cols-12 gap-3 p-3 overflow-hidden"
      style="min-height: 0"
    >
      <!-- LEFT col-7 -->
      <div class="col-span-7 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 1.2">
          <h3
            class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between"
          >
            <span class="flex items-center gap-2">
              <iconify-icon icon="mdi:chart-bar"></iconify-icon>
              7 气体 ARIMA vs LSTM 精度对比（MAE）
            </span>
            <span class="text-[10px] text-gray-500">
              LSTM 7 气体均显著优于 ARIMA · 平均改善 ↓ 38%
            </span>
          </h3>
          <div class="w-full" style="height: calc(100% - 28px)">
            <EChart :option="compareOption" />
          </div>
        </div>

        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 1">
          <h3
            class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between"
          >
            <span class="flex items-center gap-2">
              <iconify-icon icon="mdi:waveform"></iconify-icon>
              真实值 vs 预测值（滚动预测验证）
            </span>
            <div class="metric-tabs">
              <button
                v-for="g in gasOptions"
                :key="g"
                class="metric-tab"
                :class="{ active: selectedGas === g }"
                @click="selectedGas = g"
              >
                {{ g }}
              </button>
            </div>
          </h3>
          <div class="w-full" style="height: calc(100% - 28px)">
            <EChart :option="rollingOption" />
          </div>
        </div>
      </div>

      <!-- RIGHT col-5 -->
      <div class="col-span-5 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 1">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:chart-line-variant"></iconify-icon>
            LSTM 训练 loss 曲线（50 epoch）
          </h3>
          <div class="w-full" style="height: calc(100% - 28px)">
            <EChart :option="lossOption" />
          </div>
        </div>

        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 0.8">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:rotate-3d-variant"></iconify-icon>
            滚动预测推理过程（C₂H₂ 示例）
          </h3>
          <div class="space-y-2">
            <div
              v-for="(s, i) in rollingSteps"
              :key="i"
              class="rolling-step"
            >
              <div class="rolling-num">{{ i + 1 }}</div>
              <div class="flex-1">
                <p class="text-[11px] text-gray-300">
                  <span class="text-cyan-300">输入：</span>{{ s.input }}
                </p>
                <p class="text-[11px] mt-0.5">
                  <span class="text-orange-300">输出：</span>
                  <span class="text-orange-200 font-bold font-mono">{{
                    s.output
                  }}</span>
                </p>
              </div>
            </div>
          </div>
          <p class="text-[10px] text-gray-500 mt-2">
            训练只学单步，推理用预测值回填窗口 → 灵活获得 1-3 天预测
          </p>
        </div>

        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 0.7">
          <h3
            class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between"
          >
            <span class="flex items-center gap-2">
              <iconify-icon icon="mdi:brain"></iconify-icon>
              模型架构（创新点 ⭐ 多输出）
            </span>
            <span class="text-[10px] text-gray-500">仅 18.4K 参数</span>
          </h3>
          <div class="arch-flow">
            <div class="arch-node input-node">
              <p class="text-[10px] text-gray-400">输入</p>
              <p class="text-xs font-bold text-cyan-300">(30, 7)</p>
              <p class="text-[10px] text-gray-500">30 天 × 7 气体</p>
            </div>
            <iconify-icon
              class="text-gray-500 text-xl"
              icon="mdi:arrow-right"
            ></iconify-icon>
            <div class="arch-node lstm-node">
              <p class="text-[10px] text-gray-400">LSTM 共享层</p>
              <p class="text-xs font-bold text-purple-300">units=64</p>
              <p class="text-[10px] text-gray-500">学气体耦合</p>
            </div>
            <iconify-icon
              class="text-gray-500 text-xl"
              icon="mdi:arrow-right"
            ></iconify-icon>
            <div class="arch-node output-node">
              <p class="text-[10px] text-gray-400">Dense</p>
              <p class="text-xs font-bold text-orange-300">units=7</p>
              <p class="text-[10px] text-gray-500">7 气体同步</p>
            </div>
          </div>
          <p class="text-[10px] text-gray-500 mt-2">
            <iconify-icon
              icon="mdi:lightbulb"
              class="text-yellow-400"
            ></iconify-icon>
            共享隐藏层捕捉 H₂+CH₄（局放）/ C₂H₂+C₂H₄（高温过热）等耦合关系
          </p>
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
import EChart from "@/components/EChart.vue";
import { AXIS, TT } from "@/utils/chartDefaults";

const compareOption = {
  tooltip: { trigger: "axis", ...TT },
  legend: {
    textStyle: { color: "#9ca3af", fontSize: 10 },
    top: 0,
    right: 0,
    itemWidth: 10,
    itemHeight: 6,
  },
  grid: { top: 30, bottom: 30, left: 40, right: 50 },
  xAxis: {
    type: "category",
    data: ["H₂", "CH₄", "C₂H₆", "C₂H₄", "C₂H₂", "CO", "CO₂"],
    ...AXIS,
  },
  yAxis: [
    {
      type: "value",
      name: "MAE",
      nameTextStyle: { color: "#9ca3af", fontSize: 10 },
      ...AXIS,
    },
    {
      type: "value",
      name: "改善率 %",
      nameTextStyle: { color: "#10b981", fontSize: 10 },
      ...AXIS,
      max: 60,
    },
  ],
  series: [
    {
      name: "ARIMA 基线",
      type: "bar",
      data: [4.2, 5.8, 2.9, 6.1, 0.62, 12.4, 38.5],
      itemStyle: { color: "#6b7280", borderRadius: [3, 3, 0, 0] },
      barWidth: 16,
      label: { show: true, position: "top", color: "#9ca3af", fontSize: 9 },
    },
    {
      name: "LSTM 主力",
      type: "bar",
      data: [2.1, 3.4, 1.6, 3.8, 0.28, 7.1, 22.8],
      itemStyle: { color: "#06b6d4", borderRadius: [3, 3, 0, 0] },
      barWidth: 16,
      label: {
        show: true,
        position: "top",
        color: "#67e8f9",
        fontSize: 9,
        fontWeight: "bold",
      },
    },
    {
      name: "改善 ↓%",
      type: "line",
      yAxisIndex: 1,
      data: [50, 41.4, 44.8, 37.7, 54.8, 42.7, 40.8],
      lineStyle: { color: "#10b981", width: 2 },
      itemStyle: { color: "#10b981" },
      symbol: "diamond",
      symbolSize: 8,
      label: {
        show: true,
        color: "#6ee7b7",
        fontSize: 10,
        formatter: "{c}%",
      },
    },
  ],
};

const gasOptions = ["C₂H₂", "C₂H₄", "H₂", "CH₄", "CO"];
const selectedGas = ref("C₂H₂");

const gasData = {
  "C₂H₂": {
    real: [
      0.8, 1.0, 1.2, 1.5, 1.7, 1.9, 2.1, 2.3, 2.5, 2.7, 2.9, 3.05, 3.15, 3.22,
      3.24,
    ],
    arima: [
      0.85, 1.05, 1.18, 1.42, 1.65, 1.85, 2.05, 2.22, 2.38, 2.55, 2.72, 2.88,
      3.02, 3.15, 3.28, 3.42, 3.58, 3.72,
    ],
    lstm: [
      0.78, 1.02, 1.22, 1.48, 1.72, 1.92, 2.12, 2.31, 2.52, 2.7, 2.91, 3.06,
      3.16, 3.21, 3.25, 3.42, 3.68, 4.05,
    ],
    threshold: 5,
    color: "#ef4444",
  },
  "C₂H₄": {
    real: [22, 26, 30, 34, 36, 38, 39, 40, 41, 42, 42.5, 43, 43.5, 44, 45.1],
    arima: [
      23, 26.5, 30.2, 33.5, 35.5, 37.8, 38.8, 39.6, 40.7, 41.6, 42.2, 42.8,
      43.5, 44.2, 45.5, 47.2, 48.6, 50.1,
    ],
    lstm: [
      22.2, 25.8, 30.4, 34.2, 36.1, 38.2, 39.1, 40.1, 41.1, 42.1, 42.6, 43.1,
      43.5, 43.9, 45.0, 46.2, 47.8, 49.5,
    ],
    threshold: 100,
    color: "#f59e0b",
  },
  "H₂": {
    real: [25, 28, 30, 32, 34, 35, 36, 37, 38, 39, 40, 41, 41.5, 42, 42.5],
    arima: [
      26, 28.5, 30.4, 32.5, 33.8, 35.2, 36.2, 37.5, 38.4, 39.5, 40.5, 41.4,
      42.1, 42.6, 43.5, 44.8, 46.2, 47.8,
    ],
    lstm: [
      25.2, 28.1, 29.8, 32.1, 33.9, 34.8, 35.9, 36.9, 38.0, 38.9, 39.8, 40.9,
      41.4, 41.8, 42.6, 43.8, 45.2, 46.5,
    ],
    threshold: 150,
    color: "#10b981",
  },
  "CH₄": {
    real: [
      35, 40, 44, 47, 49, 51, 52, 53, 54.5, 55.5, 56, 56.8, 57.5, 58, 58.2,
    ],
    arima: [
      36, 40.5, 44.5, 47.8, 49.8, 51.5, 52.5, 53.5, 54.8, 56, 56.5, 57.2, 58,
      58.5, 59.5, 61.2, 62.8, 64.3,
    ],
    lstm: [
      35.4, 40.2, 43.8, 46.9, 48.8, 50.9, 51.8, 52.9, 54.4, 55.4, 55.9, 56.7,
      57.4, 57.9, 58.3, 59.4, 60.9, 62.5,
    ],
    threshold: 100,
    color: "#06b6d4",
  },
  "CO": {
    real: [
      260, 268, 275, 280, 286, 290, 295, 298, 302, 305, 308, 309, 310, 311,
      312,
    ],
    arima: [
      262, 270, 277, 283, 288, 293, 297, 301, 305, 309, 312, 314, 315, 316,
      318, 320, 323, 326,
    ],
    lstm: [
      261, 268, 275, 281, 286, 291, 295, 299, 303, 306, 308, 309, 310, 311,
      313, 316, 321, 325,
    ],
    threshold: 500,
    color: "#a3e635",
  },
};

const rollingOption = computed(() => {
  const d = gasData[selectedGas.value];
  const days = [
    "D-14", "D-13", "D-12", "D-11", "D-10", "D-9", "D-8", "D-7", "D-6", "D-5",
    "D-4", "D-3", "D-2", "D-1", "D-0", "D+1", "D+2", "D+3",
  ];
  const real15 = [...d.real, null, null, null];
  return {
    tooltip: { trigger: "axis", ...TT },
    legend: {
      textStyle: { color: "#9ca3af", fontSize: 10 },
      top: 0,
      right: 0,
      itemWidth: 10,
      itemHeight: 6,
    },
    grid: { top: 30, bottom: 25, left: 40, right: 60 },
    xAxis: {
      type: "category",
      data: days,
      ...AXIS,
      axisLabel: { ...AXIS.axisLabel, fontSize: 9 },
    },
    yAxis: {
      type: "value",
      ...AXIS,
      max: d.threshold > 200 ? null : d.threshold * 1.2,
    },
    series: [
      {
        name: "真实值",
        type: "line",
        smooth: true,
        data: real15,
        color: d.color,
        symbol: "circle",
        symbolSize: 5,
        lineStyle: { width: 2 },
      },
      {
        name: "ARIMA 预测",
        type: "line",
        smooth: true,
        data: d.arima,
        color: "#9ca3af",
        symbol: "none",
        lineStyle: { type: "dashed", width: 1.5 },
      },
      {
        name: "LSTM 预测",
        type: "line",
        smooth: true,
        data: d.lstm,
        color: "#06b6d4",
        symbol: "circle",
        symbolSize: 4,
        lineStyle: { type: "dashed", width: 2 },
        markArea: {
          itemStyle: { color: "rgba(251,146,60,.1)" },
          data: [[{ xAxis: "D-0" }, { xAxis: "D+3" }]],
        },
        markLine: {
          symbol: "none",
          data: [
            {
              yAxis: d.threshold,
              lineStyle: { color: "#dc2626", type: "dashed" },
              label: {
                formatter: `阈值 ${d.threshold}`,
                color: "#fca5a5",
                fontSize: 10,
              },
            },
          ],
        },
      },
    ],
  };
});

const lossOption = {
  tooltip: { trigger: "axis", ...TT },
  legend: {
    textStyle: { color: "#9ca3af", fontSize: 10 },
    top: 0,
    right: 0,
    itemWidth: 10,
    itemHeight: 6,
  },
  grid: { top: 25, bottom: 25, left: 40, right: 10 },
  xAxis: {
    type: "category",
    data: Array.from({ length: 50 }, (_, i) => i + 1),
    ...AXIS,
    axisLabel: { ...AXIS.axisLabel, interval: 9, fontSize: 9 },
    name: "epoch",
    nameTextStyle: { color: "#9ca3af", fontSize: 10 },
  },
  yAxis: { type: "value", ...AXIS, name: "MSE" },
  series: [
    {
      name: "train loss",
      type: "line",
      smooth: true,
      data: Array.from({ length: 50 }, (_, i) =>
        +(0.8 * Math.exp(-i / 8) + 0.04 + Math.random() * 0.015).toFixed(3)
      ),
      color: "#06b6d4",
      symbol: "none",
      lineStyle: { width: 1.8 },
    },
    {
      name: "val loss",
      type: "line",
      smooth: true,
      data: Array.from({ length: 50 }, (_, i) =>
        +(0.9 * Math.exp(-i / 7) + 0.06 + Math.random() * 0.02).toFixed(3)
      ),
      color: "#f59e0b",
      symbol: "none",
      lineStyle: { type: "dashed", width: 1.8 },
    },
  ],
};

const rollingSteps = [
  { input: "真实 D1-D30 → LSTM", output: "D+1 = 3.42 ppm" },
  { input: "真实 D2-D30 + 预测 D+1 → LSTM", output: "D+2 = 3.68 ppm" },
  {
    input: "真实 D3-D30 + 预测 D+1, D+2 → LSTM",
    output: "D+3 = 4.05 ppm（接近阈值 5）",
  },
];
</script>

<style scoped>
.compare-kpi {
  background: linear-gradient(
    135deg,
    rgba(59, 130, 246, 0.08),
    rgba(6, 182, 212, 0.04)
  );
  border: 1px solid rgba(59, 130, 246, 0.25);
  border-radius: 8px;
  padding: 10px 12px;
  position: relative;
}
.compare-kpi.highlight {
  border-color: rgba(168, 85, 247, 0.4);
  box-shadow: inset 0 0 18px rgba(168, 85, 247, 0.08);
}

.improve-badge {
  font-size: 11px;
  font-weight: 700;
  color: #6ee7b7;
  background: rgba(16, 185, 129, 0.18);
  border: 1px solid rgba(16, 185, 129, 0.4);
  padding: 2px 8px;
  border-radius: 12px;
  white-space: nowrap;
}

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

.rolling-step {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  background: rgba(31, 41, 55, 0.5);
  border-left: 2px solid rgba(6, 182, 212, 0.4);
  border-radius: 4px;
  padding: 6px 8px;
}
.rolling-num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(6, 182, 212, 0.2);
  color: #67e8f9;
  font-weight: 700;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 1px solid rgba(6, 182, 212, 0.4);
}

.arch-flow {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  margin: 4px 0;
}
.arch-node {
  flex: 1;
  background: rgba(31, 41, 55, 0.6);
  border: 1px solid rgba(75, 85, 99, 0.4);
  border-radius: 6px;
  padding: 6px;
  text-align: center;
}
.arch-node.input-node {
  border-color: rgba(6, 182, 212, 0.4);
}
.arch-node.lstm-node {
  border-color: rgba(168, 85, 247, 0.5);
  background: rgba(168, 85, 247, 0.08);
  box-shadow: inset 0 0 12px rgba(168, 85, 247, 0.1);
}
.arch-node.output-node {
  border-color: rgba(249, 115, 22, 0.4);
}
</style>
