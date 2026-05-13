<template>
  <div class="h-screen flex flex-col">
    <AppHeader
      title="异 常 检 测 三 方 法 对 比"
      icon="mdi:eye-check"
      subtitle="阈值法 · IEC 三比值法 · Isolation Forest"
    />

    <!-- 3 方法对比卡 -->
    <section class="px-3 pt-3 grid grid-cols-3 gap-3">
      <div
        v-for="m in methods"
        :key="m.name"
        class="method-card"
        :class="m.cls"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <iconify-icon
              class="text-3xl"
              :class="m.iconClass"
              :icon="m.icon"
            ></iconify-icon>
            <div>
              <div class="flex items-center gap-1.5">
                <span class="text-base font-bold" :class="m.titleClass">{{
                  m.name
                }}</span>
                <span
                  class="text-[10px] px-1.5 py-0.5 rounded"
                  :class="m.tag"
                  >{{ m.type }}</span
                >
              </div>
              <p class="text-[11px] text-gray-500 mt-0.5">{{ m.desc }}</p>
            </div>
          </div>
          <div v-if="m.best" class="best-badge">
            <iconify-icon icon="mdi:trophy"></iconify-icon> 最优
          </div>
        </div>
        <div class="grid grid-cols-3 gap-2 mt-2">
          <div class="metric-mini">
            <p class="text-[10px] text-gray-500">准确率</p>
            <p class="text-xl font-bold text-green-400">
              {{ m.acc }}<span class="text-[10px]">%</span>
            </p>
          </div>
          <div class="metric-mini">
            <p class="text-[10px] text-gray-500">召回率</p>
            <p class="text-xl font-bold text-cyan-400">
              {{ m.recall }}<span class="text-[10px]">%</span>
            </p>
          </div>
          <div class="metric-mini">
            <p class="text-[10px] text-gray-500">误报率</p>
            <p class="text-xl font-bold text-orange-400">
              {{ m.fpr }}<span class="text-[10px]">%</span>
            </p>
          </div>
        </div>
      </div>
    </section>

    <main
      class="flex-1 grid grid-cols-12 gap-3 p-3 overflow-hidden"
      style="min-height: 0"
    >
      <!-- LEFT col-8: comparison chart + scatter + confusion -->
      <div class="col-span-8 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 overflow-hidden" style="flex: 1.1">
          <h3
            class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between"
          >
            <span class="flex items-center gap-2">
              <iconify-icon icon="mdi:chart-bar"></iconify-icon>
              三方法 6 项指标对比（测试集 812 样本）
            </span>
            <span class="text-[10px] text-gray-500">柱越高越好（误报率越低越好）</span>
          </h3>
          <div class="w-full" style="height: calc(100% - 28px)">
            <EChart :option="compareOption" />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3 overflow-hidden" style="flex: 1">
          <div class="glass rounded-lg p-3 flex flex-col overflow-hidden">
            <h3
              class="panel-title text-sm font-bold text-cyan-300 mb-2"
            >
              <iconify-icon icon="mdi:scatter-plot"></iconify-icon>
              Isolation Forest 降维散点（PCA）
            </h3>
            <div class="flex-1" style="min-height: 0">
              <EChart :option="scatterOption" />
            </div>
          </div>

          <div class="glass rounded-lg p-3 flex flex-col overflow-hidden">
            <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
              <iconify-icon icon="mdi:gauge"></iconify-icon>
              融合投票混淆矩阵
            </h3>
            <div class="flex-1 grid grid-cols-2 gap-2" style="min-height: 0">
              <div class="conf-cell ok">
                <p class="text-[10px] text-gray-400">TP 真阳性</p>
                <p class="text-3xl font-bold text-green-300">184</p>
                <p class="text-[10px] text-gray-500">正确告警</p>
              </div>
              <div class="conf-cell warn">
                <p class="text-[10px] text-gray-400">FP 假阳性</p>
                <p class="text-3xl font-bold text-orange-300">21</p>
                <p class="text-[10px] text-gray-500">误报</p>
              </div>
              <div class="conf-cell bad">
                <p class="text-[10px] text-gray-400">FN 假阴性</p>
                <p class="text-3xl font-bold text-red-300">14</p>
                <p class="text-[10px] text-gray-500">漏报</p>
              </div>
              <div class="conf-cell neutral">
                <p class="text-[10px] text-gray-400">TN 真阴性</p>
                <p class="text-3xl font-bold text-gray-300">593</p>
                <p class="text-[10px] text-gray-500">正常无误判</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- RIGHT col-4: consistency timeline + threshold ref + ratio code -->
      <div class="col-span-4 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 flex flex-col overflow-hidden" style="flex: 1">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:timeline-check"></iconify-icon>
            近 7 日检测一致性（融合规则：≥2 异常 → 异常）
          </h3>
          <table class="consistency-table flex-1">
            <thead>
              <tr>
                <th>日期</th>
                <th>阈值</th>
                <th>三比值</th>
                <th>森林</th>
                <th>融合</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="d in dailyDetections" :key="d.day">
                <td class="text-cyan-300 font-mono text-[11px]">{{ d.day }}</td>
                <td><span class="dot-result" :class="d.threshold"></span></td>
                <td><span class="dot-result" :class="d.ratio"></span></td>
                <td><span class="dot-result" :class="d.forest"></span></td>
                <td>
                  <span
                    class="px-1.5 py-0.5 rounded text-[10px] font-bold"
                    :class="d.finalTag"
                    >{{ d.final }}</span
                  >
                </td>
              </tr>
            </tbody>
          </table>
          <p class="text-[10px] text-gray-500 mt-1.5">
            ● 异常　○ 正常 · 融合避免单方法误判
          </p>
        </div>

        <div class="glass rounded-lg p-3 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:tune-vertical"></iconify-icon>
            阈值法参考国标 DL/T 722
          </h3>
          <table class="ref-table">
            <thead>
              <tr>
                <th>气体</th>
                <th>注意值</th>
                <th>当前</th>
                <th>判定</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="t in thresholds" :key="t.gas">
                <td class="text-gray-300">{{ t.gas }}</td>
                <td class="text-gray-400">{{ t.threshold }}</td>
                <td class="font-mono" :class="t.currClass">{{ t.current }}</td>
                <td>
                  <span class="px-1.5 py-0.5 rounded text-[10px]" :class="t.tag">
                    {{ t.result }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="glass rounded-lg p-3 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:code-tags"></iconify-icon>
            三比值法编码规则
          </h3>
          <div class="grid grid-cols-3 gap-1.5 text-[10px]">
            <div class="code-cell">
              <p class="text-cyan-300 font-bold">C₂H₂/C₂H₄</p>
              <p>&lt;0.1 → 0</p>
              <p>0.1-3 → 1</p>
              <p>&gt;3 → 2</p>
            </div>
            <div class="code-cell">
              <p class="text-cyan-300 font-bold">CH₄/H₂</p>
              <p>&lt;0.1 → 1</p>
              <p>0.1-1 → 0</p>
              <p>&gt;1 → 2</p>
            </div>
            <div class="code-cell">
              <p class="text-cyan-300 font-bold">C₂H₄/C₂H₆</p>
              <p>&lt;1 → 0</p>
              <p>1-3 → 1</p>
              <p>&gt;3 → 2</p>
            </div>
          </div>
          <div
            class="mt-2 p-1.5 bg-orange-500/10 border border-orange-500/30 rounded flex justify-between items-center"
          >
            <span class="text-[11px] text-gray-400">当前编码</span>
            <span class="text-[11px] text-orange-300 font-bold">
              021 → 低温过热 (&lt;300℃)
            </span>
          </div>
        </div>
      </div>
    </main>

    <AppFooter />
  </div>
</template>

<script setup>
import AppHeader from "@/components/AppHeader.vue";
import AppFooter from "@/components/AppFooter.vue";
import EChart from "@/components/EChart.vue";
import { AXIS, TT } from "@/utils/chartDefaults";

const methods = [
  {
    name: "阈值法",
    desc: "国标 DL/T 722 注意值",
    icon: "mdi:tune-vertical",
    iconClass: "text-blue-400",
    titleClass: "text-blue-300",
    type: "规则类",
    tag: "tag-blu",
    cls: "border-blue-500/40",
    acc: 88.2,
    recall: 82.5,
    fpr: 9.1,
    best: false,
  },
  {
    name: "IEC 三比值法",
    desc: "国标诊断 · 编码故障类型",
    icon: "mdi:calculator-variant",
    iconClass: "text-orange-400",
    titleClass: "text-orange-300",
    type: "规则类",
    tag: "tag-org",
    cls: "border-orange-500/40",
    acc: 91.5,
    recall: 87.3,
    fpr: 6.8,
    best: false,
  },
  {
    name: "Isolation Forest",
    desc: "sklearn · 无监督机器学习",
    icon: "mdi:pine-tree",
    iconClass: "text-green-400",
    titleClass: "text-green-300",
    type: "机器学习",
    tag: "tag-grn",
    cls: "border-green-500/40 highlight",
    acc: 94.1,
    recall: 91.2,
    fpr: 4.7,
    best: true,
  },
];

const compareOption = {
  tooltip: { trigger: "axis", ...TT },
  legend: {
    textStyle: { color: "#9ca3af", fontSize: 10 },
    top: 0,
    right: 0,
    itemWidth: 10,
    itemHeight: 6,
  },
  grid: { top: 30, bottom: 25, left: 40, right: 10 },
  xAxis: {
    type: "category",
    data: ["准确率", "精确率", "召回率", "F1-Score", "AUC", "误报率"],
    ...AXIS,
  },
  yAxis: {
    type: "value",
    ...AXIS,
    max: 100,
    axisLabel: { ...AXIS.axisLabel, formatter: "{value}%" },
  },
  series: [
    {
      name: "阈值法",
      type: "bar",
      data: [88.2, 85.3, 82.5, 83.9, 86.4, 9.1],
      itemStyle: { color: "#3b82f6", borderRadius: [3, 3, 0, 0] },
      barWidth: 14,
    },
    {
      name: "IEC 三比值法",
      type: "bar",
      data: [91.5, 89.7, 87.3, 88.5, 90.2, 6.8],
      itemStyle: { color: "#f97316", borderRadius: [3, 3, 0, 0] },
      barWidth: 14,
    },
    {
      name: "Isolation Forest",
      type: "bar",
      data: [94.1, 92.8, 91.2, 92.0, 94.6, 4.7],
      itemStyle: { color: "#10b981", borderRadius: [3, 3, 0, 0] },
      barWidth: 14,
    },
  ],
};

const scatterData = [];
for (let i = 0; i < 220; i++) {
  scatterData.push([
    +(Math.random() * 2 - 1).toFixed(3),
    +(Math.random() * 2 - 1).toFixed(3),
    "normal",
  ]);
}
for (let i = 0; i < 16; i++) {
  scatterData.push([
    +(Math.random() * 3 + 1.5).toFixed(3),
    +(Math.random() * 3 - 2.5).toFixed(3),
    "anomaly",
  ]);
}

const scatterOption = {
  tooltip: {
    ...TT,
    formatter: (p) => `PC1=${p.data[0]}<br/>PC2=${p.data[1]}<br/>${p.data[2]}`,
  },
  legend: {
    textStyle: { color: "#9ca3af", fontSize: 10 },
    top: 0,
    right: 0,
  },
  grid: { top: 25, bottom: 20, left: 36, right: 10 },
  xAxis: {
    type: "value",
    name: "PC1",
    nameTextStyle: { color: "#9ca3af", fontSize: 10 },
    ...AXIS,
  },
  yAxis: {
    type: "value",
    name: "PC2",
    nameTextStyle: { color: "#9ca3af", fontSize: 10 },
    ...AXIS,
  },
  series: [
    {
      name: "正常",
      type: "scatter",
      data: scatterData.filter((d) => d[2] === "normal"),
      symbolSize: 6,
      itemStyle: { color: "rgba(16, 185, 129, .55)" },
    },
    {
      name: "异常",
      type: "scatter",
      data: scatterData.filter((d) => d[2] === "anomaly"),
      symbolSize: 11,
      itemStyle: {
        color: "#ef4444",
        shadowBlur: 8,
        shadowColor: "#ef4444",
      },
    },
  ],
};

const dailyDetections = [
  { day: "D-6", threshold: "ok", ratio: "ok", forest: "ok", final: "正常", finalTag: "tag-grn" },
  { day: "D-5", threshold: "ok", ratio: "ok", forest: "bad", final: "正常", finalTag: "tag-grn" },
  { day: "D-4", threshold: "ok", ratio: "bad", forest: "bad", final: "异常", finalTag: "tag-org" },
  { day: "D-3", threshold: "ok", ratio: "bad", forest: "bad", final: "异常", finalTag: "tag-org" },
  { day: "D-2", threshold: "bad", ratio: "bad", forest: "bad", final: "异常", finalTag: "tag-red" },
  { day: "D-1", threshold: "bad", ratio: "bad", forest: "bad", final: "异常", finalTag: "tag-red" },
  { day: "今日", threshold: "bad", ratio: "bad", forest: "bad", final: "异常", finalTag: "tag-red" },
];

const thresholds = [
  { gas: "H₂",   threshold: "150 ppm", current: "42.5",  currClass: "text-green-400",  result: "正常", tag: "tag-grn" },
  { gas: "C₂H₂", threshold: "5 ppm",   current: "3.24",  currClass: "text-red-400",    result: "趋近", tag: "tag-red" },
  { gas: "C₂H₄", threshold: "100 ppm", current: "45.1",  currClass: "text-yellow-400", result: "关注", tag: "tag-yel" },
  { gas: "总烃", threshold: "150 ppm", current: "129.3", currClass: "text-yellow-400", result: "关注", tag: "tag-yel" },
];
</script>

<style scoped>
.method-card {
  background: rgba(17, 24, 39, 0.7);
  border: 1px solid;
  border-radius: 8px;
  padding: 12px;
  position: relative;
}
.method-card.highlight {
  box-shadow: 0 0 24px rgba(16, 185, 129, 0.15),
    inset 0 0 20px rgba(16, 185, 129, 0.08);
}

.best-badge {
  font-size: 10px;
  color: #6ee7b7;
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.4);
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 3px;
}

.metric-mini {
  background: rgba(31, 41, 55, 0.5);
  border-radius: 4px;
  padding: 4px 6px;
  text-align: center;
}

.consistency-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}
.consistency-table th {
  color: #9ca3af;
  font-weight: 500;
  padding: 4px;
  text-align: center;
  border-bottom: 1px solid rgba(75, 85, 99, 0.4);
  background: rgba(31, 41, 55, 0.5);
  font-size: 10px;
}
.consistency-table td {
  padding: 5px 4px;
  text-align: center;
  border-bottom: 1px solid rgba(55, 65, 81, 0.3);
}
.dot-result {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
}
.dot-result.ok {
  background: #10b981;
  box-shadow: 0 0 4px rgba(16, 185, 129, 0.5);
}
.dot-result.bad {
  background: #ef4444;
  box-shadow: 0 0 4px rgba(239, 68, 68, 0.5);
}

.ref-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}
.ref-table th {
  color: #9ca3af;
  font-weight: 500;
  padding: 4px 6px;
  text-align: left;
  border-bottom: 1px solid rgba(75, 85, 99, 0.4);
  font-size: 10px;
}
.ref-table td {
  padding: 4px 6px;
  border-bottom: 1px solid rgba(55, 65, 81, 0.25);
}

.code-cell {
  background: rgba(31, 41, 55, 0.6);
  border: 1px solid rgba(75, 85, 99, 0.35);
  border-radius: 4px;
  padding: 6px;
  color: #d1d5db;
  line-height: 1.55;
}

.conf-cell {
  border: 1px solid;
  border-radius: 6px;
  padding: 8px;
  text-align: center;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.conf-cell.ok {
  border-color: rgba(16, 185, 129, 0.4);
  background: rgba(16, 185, 129, 0.1);
}
.conf-cell.warn {
  border-color: rgba(245, 158, 11, 0.4);
  background: rgba(245, 158, 11, 0.1);
}
.conf-cell.bad {
  border-color: rgba(239, 68, 68, 0.4);
  background: rgba(239, 68, 68, 0.1);
}
.conf-cell.neutral {
  border-color: rgba(107, 114, 128, 0.4);
  background: rgba(107, 114, 128, 0.1);
}
</style>
