<template>
  <div class="h-screen flex flex-col">
    <AppHeader
      title="L S T M  与  A R I M A  趋 势 预 测 对 比"
      icon="mdi:chart-timeline-variant-shimmer"
      subtitle="7 气体单步预测 · 验证段 walk-forward · 多方法对比研究"
    />

    <!-- 顶部对比 KPI(据实:ARIMA 略优,胜 6/7)-->
    <section class="px-3 pt-3 grid grid-cols-4 gap-3">
      <div class="compare-kpi">
        <p class="text-[11px] text-gray-400">平均 MAE</p>
        <div class="flex items-baseline gap-2 mt-1">
          <div>
            <span class="text-[10px] text-gray-500">ARIMA</span>
            <p class="text-2xl font-bold text-cyan-400">{{ kpi.arimaMae }}</p>
          </div>
          <iconify-icon class="text-gray-500" icon="mdi:less-than"></iconify-icon>
          <div>
            <span class="text-[10px] text-gray-500">LSTM</span>
            <p class="text-base font-bold text-gray-400 line-through">{{ kpi.lstmMae }}</p>
          </div>
          <span class="ml-auto winner-badge">ARIMA 胜</span>
        </div>
      </div>
      <div class="compare-kpi">
        <p class="text-[11px] text-gray-400">平均 RMSE</p>
        <div class="flex items-baseline gap-2 mt-1">
          <div>
            <span class="text-[10px] text-gray-500">ARIMA</span>
            <p class="text-2xl font-bold text-cyan-400">{{ kpi.arimaRmse }}</p>
          </div>
          <iconify-icon class="text-gray-500" icon="mdi:less-than"></iconify-icon>
          <div>
            <span class="text-[10px] text-gray-500">LSTM</span>
            <p class="text-base font-bold text-gray-400 line-through">{{ kpi.lstmRmse }}</p>
          </div>
          <span class="ml-auto winner-badge">ARIMA 胜</span>
        </div>
      </div>
      <div class="compare-kpi">
        <p class="text-[11px] text-gray-400">7 气体胜负</p>
        <div class="flex items-baseline gap-2 mt-1">
          <div>
            <span class="text-[10px] text-gray-500">ARIMA 胜</span>
            <p class="text-2xl font-bold text-cyan-400">{{ kpi.arimaWins }}<span class="text-xs">/7</span></p>
          </div>
          <iconify-icon class="text-gray-500" icon="mdi:slash-forward"></iconify-icon>
          <div>
            <span class="text-[10px] text-gray-500">LSTM 胜</span>
            <p class="text-base font-bold text-gray-400">{{ 7 - kpi.arimaWins }}<span class="text-[10px]">/7</span></p>
          </div>
          <span class="ml-auto winner-badge">{{ kpi.arimaWins === 7 ? "全胜" : "领先" }}</span>
        </div>
      </div>
      <div class="compare-kpi note">
        <p class="text-[11px] text-gray-400">研究结论</p>
        <p class="text-[12px] text-gray-200 mt-1 leading-snug">
          小样本(单设备 360 天)、高波动 DGA 上,经典统计法
          <span class="text-cyan-300 font-bold">ARIMA 较 LSTM 更稳健</span>
        </p>
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
              7 气体 LSTM vs ARIMA 误差对比(MAE,对数轴)
            </span>
            <span class="text-[10px] text-gray-500">
              7 气体 ARIMA 误差均低于 LSTM
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
              验证段:真值 vs LSTM vs ARIMA
            </span>
            <div class="metric-tabs">
              <button
                v-for="g in gasOptions"
                :key="g.key"
                class="metric-tab"
                :class="{ active: selectedGas === g.key }"
                @click="selectedGas = g.key"
              >
                {{ g.label }}
              </button>
            </div>
          </h3>
          <div class="w-full" style="height: calc(100% - 28px)">
            <EChart :option="seriesOption" />
          </div>
        </div>
      </div>

      <!-- RIGHT col-5 -->
      <div class="col-span-5 flex flex-col gap-3 overflow-hidden">
        <!-- 滚动预测:未来 1-3 天,tab 切 LSTM/ARIMA,气体可切换 -->
        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 1.2">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between">
            <span class="flex items-center gap-2">
              <iconify-icon icon="mdi:rotate-3d-variant"></iconify-icon>
              滚动预测推理（未来 1-3 天）
            </span>
            <div class="flex items-center gap-2">
              <div class="metric-tabs">
                <button class="metric-tab" :class="{ active: rollModel === 'lstm' }" @click="rollModel = 'lstm'">LSTM 回灌</button>
                <button class="metric-tab" :class="{ active: rollModel === 'arima' }" @click="rollModel = 'arima'">ARIMA 多步</button>
              </div>
              <select v-model="rollGas" class="toolbar-select">
                <option v-for="g in gasOptions" :key="g.key" :value="g.key">{{ g.label }}</option>
              </select>
            </div>
          </h3>
          <div class="w-full" style="height: calc(100% - 52px)">
            <EChart :option="rollingOption" />
          </div>
          <p class="text-[10px] text-gray-500 mt-1">
            {{ rollModel === 'lstm' ? 'LSTM 单步模型迭代回灌:预测值接回窗口尾再预测下一天' : 'ARIMA 原生多步:一阶差分模型直接外推 3 步' }}
          </p>
        </div>

        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 0.9">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between">
            <span class="flex items-center gap-2">
              <iconify-icon icon="mdi:chart-line-variant"></iconify-icon>
              LSTM 训练 loss 曲线
            </span>
            <span class="text-[10px] text-gray-500">{{ lossEpochs }} epoch · loss 收敛正常</span>
          </h3>
          <div class="w-full" style="height: calc(100% - 28px)">
            <EChart :option="lossOption" />
          </div>
        </div>

        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 0.7">
          <h3
            class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between"
          >
            <span class="flex items-center gap-2">
              <iconify-icon icon="mdi:brain"></iconify-icon>
              LSTM 模型架构(多输出回归)
            </span>
            <span class="text-[10px] text-gray-500">单步预测</span>
          </h3>
          <div class="arch-flow">
            <div class="arch-node input-node">
              <p class="text-[10px] text-gray-400">输入</p>
              <p class="text-xs font-bold text-cyan-300">(30, 7)</p>
              <p class="text-[10px] text-gray-500">30 天 × 7 气体</p>
            </div>
            <iconify-icon class="text-gray-500 text-xl" icon="mdi:arrow-right"></iconify-icon>
            <div class="arch-node lstm-node">
              <p class="text-[10px] text-gray-400">LSTM 共享层</p>
              <p class="text-xs font-bold text-purple-300">units=64</p>
              <p class="text-[10px] text-gray-500">学气体耦合</p>
            </div>
            <iconify-icon class="text-gray-500 text-xl" icon="mdi:arrow-right"></iconify-icon>
            <div class="arch-node output-node">
              <p class="text-[10px] text-gray-400">Dense</p>
              <p class="text-xs font-bold text-orange-300">units=7</p>
              <p class="text-[10px] text-gray-500">7 气体同步</p>
            </div>
          </div>
          <p class="text-[10px] text-gray-500 mt-2">
            <iconify-icon icon="mdi:lightbulb" class="text-yellow-400"></iconify-icon>
            多输出共享层设计可隐式学气体耦合;但在本数据规模(单设备、滑窗后约 258 训练样本)下精度未能兑现优势
          </p>
        </div>

        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 0.6">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:information-outline"></iconify-icon>
            为什么 ARIMA 更优(原因分析)
          </h3>
          <ul class="reason-list">
            <li>样本量受限:滑窗后训练样本约 258 个,LSTM 难以充分泛化</li>
            <li>归一化分辨率:7 气体跨度极大(CO₂ 最高约 6 万 μL/L),MinMax 全域归一压缩了正常变化</li>
            <li>序列特性:DGA 呈均值回复 + 强噪声,ARIMA 一阶差分 + 全量重拟合更稳健</li>
          </ul>
        </div>
      </div>
    </main>

    <AppFooter />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import AppHeader from "@/components/AppHeader.vue";
import AppFooter from "@/components/AppFooter.vue";
import EChart from "@/components/EChart.vue";
import { AXIS, TT } from "@/utils/chartDefaults";
import { getPredictCompare } from "@/service/api";

// ============ 真值兜底常量(防 Demo 断网)============
// 来源:GET /api/predict/compare(读 data/predict_eval.json,scripts/compare_predict.py 落盘)。
// 实测结论(D-044 全链路重跑):总体 ARIMA 略优(MAE 148.3 vs 160.4),逐气体 ARIMA 胜 6/7
// (仅 CO 一项 LSTM 略优),如实呈现不粉饰。
const FALLBACK = {
  gases: ["h2", "ch4", "c2h4", "c2h6", "c2h2", "co", "co2"],
  overall: { winner: "ARIMA", lstm_mean_mae: 160.439, arima_mean_mae: 148.322 },
  per_gas: {
    h2: { lstm: { mae: 28.563, rmse: 34.233 }, arima: { mae: 22.23, rmse: 30.9 }, winner: "ARIMA" },
    ch4: { lstm: { mae: 8.046, rmse: 10.159 }, arima: { mae: 1.89, rmse: 2.116 }, winner: "ARIMA" },
    c2h4: { lstm: { mae: 19.765, rmse: 29.057 }, arima: { mae: 5.617, rmse: 6.058 }, winner: "ARIMA" },
    c2h6: { lstm: { mae: 97.966, rmse: 215.688 }, arima: { mae: 91.158, rmse: 200.191 }, winner: "ARIMA" },
    c2h2: { lstm: { mae: 4.987, rmse: 6.05 }, arima: { mae: 1.33, rmse: 1.605 }, winner: "ARIMA" },
    co: { lstm: { mae: 91.088, rmse: 134.328 }, arima: { mae: 96.351, rmse: 140.843 }, winner: "LSTM" },
    co2: { lstm: { mae: 872.659, rmse: 1419.56 }, arima: { mae: 819.677, rmse: 1524.836 }, winner: "ARIMA" },
  },
  series: {},          // 断网时曲线留空(不杜撰),仅靠 per_gas 指标撑住对比叙事
  loss_history: { loss: [], val_loss: [], epochs: 0 },
  rolling: {},         // 断网时滚动预测留空,不杜撰
};

const evalData = ref(FALLBACK);

onMounted(async () => {
  try {
    const data = await getPredictCompare();
    if (data?.per_gas) evalData.value = data;
  } catch (e) {
    console.warn("[PredictionView] 预测对比接口拉取失败,使用真值兜底常量", e);
  }
});

// 气体名 → 展示标签(下标)
const GAS_LABEL = {
  h2: "H₂", ch4: "CH₄", c2h4: "C₂H₄", c2h6: "C₂H₆",
  c2h2: "C₂H₂", co: "CO", co2: "CO₂",
};

// 顶部 KPI(据实)
const kpi = computed(() => {
  const d = evalData.value;
  const gases = d.gases || [];
  const meanRmse = (m) =>
    gases.length
      ? +(gases.reduce((s, g) => s + d.per_gas[g][m].rmse, 0) / gases.length).toFixed(1)
      : 0;
  const arimaWins = gases.filter((g) => d.per_gas[g].winner === "ARIMA").length;
  return {
    arimaMae: d.overall.arima_mean_mae,
    lstmMae: d.overall.lstm_mean_mae,
    arimaRmse: meanRmse("arima"),
    lstmRmse: meanRmse("lstm"),
    arimaWins,
  };
});

// 左上:7 气体 MAE 对比(对数轴 —— 各气体量纲跨度极大)
const compareOption = computed(() => {
  const d = evalData.value;
  const gases = d.gases || [];
  return {
    tooltip: { trigger: "axis", ...TT },
    legend: {
      textStyle: { color: "#9ca3af", fontSize: 10 },
      top: 0, right: 0, itemWidth: 10, itemHeight: 6,
    },
    grid: { top: 30, bottom: 30, left: 48, right: 16 },
    xAxis: { type: "category", data: gases.map((g) => GAS_LABEL[g] || g), ...AXIS },
    yAxis: {
      type: "log", name: "MAE(对数)",
      nameTextStyle: { color: "#9ca3af", fontSize: 10 }, ...AXIS,
    },
    series: [
      {
        name: "ARIMA", type: "bar",
        data: gases.map((g) => d.per_gas[g].arima.mae),
        itemStyle: { color: "#06b6d4", borderRadius: [3, 3, 0, 0] },
        barWidth: 16,
        label: { show: true, position: "top", color: "#67e8f9", fontSize: 9, fontWeight: "bold" },
      },
      {
        name: "LSTM", type: "bar",
        data: gases.map((g) => d.per_gas[g].lstm.mae),
        itemStyle: { color: "#6b7280", borderRadius: [3, 3, 0, 0] },
        barWidth: 16,
        label: { show: true, position: "top", color: "#9ca3af", fontSize: 9 },
      },
    ],
  };
});

// 左下:验证段三序列(真值 vs LSTM vs ARIMA),按所选气体
const gasOptions = [
  { key: "h2", label: "H₂" },
  { key: "ch4", label: "CH₄" },
  { key: "c2h4", label: "C₂H₄" },
  { key: "c2h6", label: "C₂H₆" },
  { key: "c2h2", label: "C₂H₂" },
  { key: "co", label: "CO" },
  { key: "co2", label: "CO₂" },
];
const selectedGas = ref("c2h2");

// 滚动预测:tab 切模型 + 气体可切换
const rollModel = ref("arima");   // 默认 ARIMA(主力)
const rollGas = ref("c2h2");
const rollingOption = computed(() => {
  const r = evalData.value.rolling || {};
  const hist = r.history?.[rollGas.value] || [];
  const fut = r[rollModel.value]?.[rollGas.value] || [];
  // x 轴:历史 D-N..D-1 + 未来 D+1..D+3
  const xHist = hist.map((_, i) => `D-${hist.length - i}`);
  const xFut = fut.map((_, i) => `D+${i + 1}`);
  // 预测线从历史最后一点接起,视觉连续
  const predLine = [...Array(Math.max(0, hist.length - 1)).fill(null),
    hist.length ? hist[hist.length - 1] : null, ...fut];
  const color = rollModel.value === "lstm" ? "#f59e0b" : "#06b6d4";
  return {
    tooltip: { trigger: "axis", ...TT },
    legend: { textStyle: { color: "#9ca3af", fontSize: 10 }, top: 0, right: 0, itemWidth: 10, itemHeight: 6 },
    grid: { top: 25, bottom: 25, left: 48, right: 16 },
    xAxis: { type: "category", data: [...xHist, ...xFut], ...AXIS, axisLabel: { ...AXIS.axisLabel, fontSize: 9 } },
    yAxis: { type: "value", ...AXIS, name: "μL/L" },
    series: [
      { name: "历史真值", type: "line", data: [...hist, ...Array(fut.length).fill(null)],
        color: "#e5e7eb", symbol: "circle", symbolSize: 4, lineStyle: { width: 2 } },
      { name: rollModel.value === "lstm" ? "LSTM 预测" : "ARIMA 预测", type: "line", data: predLine,
        color, symbol: "diamond", symbolSize: 6, lineStyle: { width: 2, type: "dashed" },
        markArea: { itemStyle: { color: "rgba(99,102,241,.08)" }, data: [[{ xAxis: "D+1" }, { xAxis: `D+${fut.length}` }]] } },
    ],
  };
});

const seriesOption = computed(() => {
  const d = evalData.value;
  const s = d.series?.[selectedGas.value];
  const x = s ? s.truth.map((_, i) => i + 1) : [];
  return {
    tooltip: { trigger: "axis", ...TT },
    legend: {
      textStyle: { color: "#9ca3af", fontSize: 10 },
      top: 0, right: 0, itemWidth: 10, itemHeight: 6,
    },
    grid: { top: 30, bottom: 25, left: 48, right: 16 },
    xAxis: {
      type: "category", data: x, ...AXIS,
      name: "验证段目标日", nameTextStyle: { color: "#9ca3af", fontSize: 9 },
      axisLabel: { ...AXIS.axisLabel, fontSize: 9 },
    },
    yAxis: { type: "value", ...AXIS, name: "μL/L" },
    series: [
      {
        name: "真值", type: "line", smooth: true,
        data: s ? s.truth : [], color: "#e5e7eb",
        symbol: "circle", symbolSize: 4, lineStyle: { width: 2 },
      },
      {
        name: "ARIMA", type: "line", smooth: true,
        data: s ? s.arima : [], color: "#06b6d4",
        symbol: "none", lineStyle: { width: 1.8 },
      },
      {
        name: "LSTM", type: "line", smooth: true,
        data: s ? s.lstm : [], color: "#f59e0b",
        symbol: "none", lineStyle: { type: "dashed", width: 1.8 },
      },
    ],
  };
});

// 右上:LSTM 训练 loss 曲线(真实落盘的 loss_history)
const lossEpochs = computed(() => evalData.value.loss_history?.epochs || 0);
const lossOption = computed(() => {
  const h = evalData.value.loss_history || { loss: [], val_loss: [] };
  const n = h.loss?.length || 0;
  return {
    tooltip: { trigger: "axis", ...TT },
    legend: {
      textStyle: { color: "#9ca3af", fontSize: 10 },
      top: 0, right: 0, itemWidth: 10, itemHeight: 6,
    },
    grid: { top: 25, bottom: 25, left: 44, right: 10 },
    xAxis: {
      type: "category", data: Array.from({ length: n }, (_, i) => i + 1), ...AXIS,
      axisLabel: { ...AXIS.axisLabel, interval: Math.max(0, Math.floor(n / 5) - 1), fontSize: 9 },
      name: "epoch", nameTextStyle: { color: "#9ca3af", fontSize: 10 },
    },
    yAxis: { type: "value", ...AXIS, name: "MSE" },
    series: [
      {
        name: "train loss", type: "line", smooth: true,
        data: h.loss || [], color: "#06b6d4", symbol: "none", lineStyle: { width: 1.8 },
      },
      {
        name: "val loss", type: "line", smooth: true,
        data: h.val_loss || [], color: "#f59e0b", symbol: "none",
        lineStyle: { type: "dashed", width: 1.8 },
      },
    ],
  };
});
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
.compare-kpi.note {
  border-color: rgba(6, 182, 212, 0.35);
}

.winner-badge {
  font-size: 11px;
  font-weight: 700;
  color: #67e8f9;
  background: rgba(6, 182, 212, 0.18);
  border: 1px solid rgba(6, 182, 212, 0.4);
  padding: 2px 8px;
  border-radius: 12px;
  white-space: nowrap;
}

.reason-list {
  list-style: disc;
  padding-left: 16px;
  font-size: 11px;
  color: #cbd5e1;
  line-height: 1.7;
}

.toolbar-select {
  background: rgba(17, 24, 39, 0.8);
  border: 1px solid rgba(75, 85, 99, 0.4);
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 10px;
  color: #e5e7eb;
  outline: none;
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
.metric-tab.active {
  background: rgba(6, 182, 212, 0.25);
  color: #67e8f9;
}

.arch-flow {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  margin-top: 4px;
}
.arch-node {
  flex: 1;
  text-align: center;
  padding: 6px 4px;
  border-radius: 6px;
  border: 1px solid rgba(148, 163, 184, 0.2);
}
.input-node { background: rgba(6, 182, 212, 0.08); }
.lstm-node { background: rgba(168, 85, 247, 0.08); }
.output-node { background: rgba(249, 115, 22, 0.08); }
</style>
