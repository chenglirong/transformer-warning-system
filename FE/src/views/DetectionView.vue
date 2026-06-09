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
              三方法 5 项指标对比（{{ compare.n_samples }} 天合成时序 · 真值异常 {{ compare.n_abnormal_truth }}）
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
              class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center gap-1.5"
            >
              <iconify-icon icon="mdi:scatter-plot"></iconify-icon>
              Isolation Forest 降维散点（PCA）
              <span class="demo-badge">示意</span>
            </h3>
            <div class="flex-1" style="min-height: 0">
              <EChart :option="scatterOption" />
            </div>
          </div>

          <div class="glass rounded-lg p-3 flex flex-col overflow-hidden">
            <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
              <iconify-icon icon="mdi:gauge"></iconify-icon>
              Isolation Forest 混淆矩阵（最优方法）
            </h3>
            <div class="flex-1 grid grid-cols-2 gap-2" style="min-height: 0">
              <div class="conf-cell ok">
                <p class="text-[10px] text-gray-400">TP 真阳性</p>
                <p class="text-3xl font-bold text-green-300">{{ iforestConfusion.tp }}</p>
                <p class="text-[10px] text-gray-500">正确告警</p>
              </div>
              <div class="conf-cell warn">
                <p class="text-[10px] text-gray-400">FP 假阳性</p>
                <p class="text-3xl font-bold text-orange-300">{{ iforestConfusion.fp }}</p>
                <p class="text-[10px] text-gray-500">误报</p>
              </div>
              <div class="conf-cell bad">
                <p class="text-[10px] text-gray-400">FN 假阴性</p>
                <p class="text-3xl font-bold text-red-300">{{ iforestConfusion.fn }}</p>
                <p class="text-[10px] text-gray-500">漏报</p>
              </div>
              <div class="conf-cell neutral">
                <p class="text-[10px] text-gray-400">TN 真阴性</p>
                <p class="text-3xl font-bold text-gray-300">{{ iforestConfusion.tn }}</p>
                <p class="text-[10px] text-gray-500">正常无误判</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- RIGHT col-4: consistency timeline + threshold ref + ratio code -->
      <div class="col-span-4 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 flex flex-col overflow-hidden" style="flex: 1">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center gap-1.5">
            <iconify-icon icon="mdi:timeline-check"></iconify-icon>
            近 7 日检测一致性（融合规则：≥2 异常 → 异常）
            <span class="demo-badge">示意</span>
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
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center gap-1.5">
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
          <!-- 系统边界:三比值编码规则可作科普展示,但禁止推出并展示具体故障类型 -->
          <!-- (原"021 → 低温过热"已删除,IEC 故障类型属诊断系统职责,见 docs/04-architecture.md)-->
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
import { getDetectCompare, getLatest } from "@/service/api";

// ============ 真值兜底常量(防 Demo 断网)============
// 来源:scripts/compare_detection.py / GET /api/detect/_internal/compare
// 基准=合成真值 fault_state,n=360,真值异常 91(D-020/D-021)。
// 单位为比率(0~1),展示时 ×100 转百分比。
const FALLBACK = {
  n_samples: 360,
  n_abnormal_truth: 91,
  metrics: {
    threshold: { accuracy: 0.6056, precision: 0.3679, recall: 0.7802, f1: 0.5, fpr: 0.4535,
      confusion: { tp: 71, tn: 147, fp: 122, fn: 20 } },
    iec: { accuracy: 0.675, precision: 0.37, recall: 0.4066, f1: 0.3874, fpr: 0.2342,
      confusion: { tp: 37, tn: 206, fp: 63, fn: 54 } },
    iforest: { accuracy: 0.8028, precision: 0.6111, recall: 0.6044, f1: 0.6077, fpr: 0.1301,
      confusion: { tp: 55, tn: 234, fp: 35, fn: 36 } },
  },
};

// 实时拉取的对比数据;拉取失败回退到 FALLBACK
const compare = ref(FALLBACK);

// 单台最新一条监测(阈值参考表用真实气体值)
const TRANSFORMER_ID = 1; // 单设备方案
const latest = ref(null);

const pct = (x) => +(x * 100).toFixed(1); // 比率 → 百分比(1 位小数)

onMounted(async () => {
  try {
    const data = await getDetectCompare();
    if (data?.metrics) compare.value = data;
  } catch (e) {
    // 静默回退到真值兜底常量,保证 Demo 可离线展示
    console.warn("[DetectionView] 对比接口拉取失败,使用真值兜底常量", e);
  }
  try {
    latest.value = await getLatest(TRANSFORMER_ID);
  } catch (e) {
    console.warn("[DetectionView] latest 拉取失败,阈值表显示占位", e);
  }
});

// ① 三方法卡片:指标来自 compare.value.metrics(真值,非杜撰)
// 卡片只展示「准确率 / 召回率 / 误报率」三项,完整 6 项见下方柱状图
const methods = computed(() => {
  const m = compare.value.metrics;
  return [
    {
      name: "阈值法",
      desc: "国标 DL/T 722 注意值",
      icon: "mdi:tune-vertical",
      iconClass: "text-blue-400",
      titleClass: "text-blue-300",
      type: "规则类",
      tag: "tag-blu",
      cls: "border-blue-500/40",
      acc: pct(m.threshold.accuracy),
      recall: pct(m.threshold.recall),
      fpr: pct(m.threshold.fpr),
      best: false,
    },
    {
      name: "IEC 三比值法",
      desc: "国标比值法 · 内部分组用",
      icon: "mdi:calculator-variant",
      iconClass: "text-orange-400",
      titleClass: "text-orange-300",
      type: "规则类",
      tag: "tag-org",
      cls: "border-orange-500/40",
      acc: pct(m.iec.accuracy),
      recall: pct(m.iec.recall),
      fpr: pct(m.iec.fpr),
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
      acc: pct(m.iforest.accuracy),
      recall: pct(m.iforest.recall),
      fpr: pct(m.iforest.fpr),
      best: true, // F1 最高、误报率最低(D-021)
    },
  ];
});

// ② 6 项指标柱状图 → 真值,5 项(砍掉后端未计算的 AUC)
// 一个方法的指标按 [准确率,精确率,召回率,F1,误报率] 排列,均 ×100
const metricRow = (mm) =>
  [mm.accuracy, mm.precision, mm.recall, mm.f1, mm.fpr].map((v) => pct(v));

const compareOption = computed(() => {
  const m = compare.value.metrics;
  return {
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
      data: ["准确率", "精确率", "召回率", "F1-Score", "误报率"],
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
        data: metricRow(m.threshold),
        itemStyle: { color: "#3b82f6", borderRadius: [3, 3, 0, 0] },
        barWidth: 14,
      },
      {
        name: "IEC 三比值法",
        type: "bar",
        data: metricRow(m.iec),
        itemStyle: { color: "#f97316", borderRadius: [3, 3, 0, 0] },
        barWidth: 14,
      },
      {
        name: "Isolation Forest",
        type: "bar",
        data: metricRow(m.iforest),
        itemStyle: { color: "#10b981", borderRadius: [3, 3, 0, 0] },
        barWidth: 14,
      },
    ],
  };
});

// ③ 混淆矩阵:展示最优方法 Isolation Forest 的真实四格(D-021)
const iforestConfusion = computed(() => compare.value.metrics.iforest.confusion);

// ⚠️ 以下为右侧栏示意数据(Y2):散点/近7日一致性/阈值参考表
// 本周仅接左侧指标对比真值,右侧明细待第 8 周联调时接业务接口。
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

// 阈值参考表:接 latest.gases 真实气体值,阈值口径与后端 ATTENTION_VALUES 一致
// (threshold.py:h2=150 / c2h2=5 / 总烃=150 / co=300;单个烃类不单设,按总烃合并判)
// 判定分档:超注意值→异常;≥80%→趋近;≥50%→关注;否则正常
const ATTENTION = { h2: 150, c2h2: 5, total_hydrocarbon: 150, co: 300 };

const judge = (v, limit) => {
  const ratio = v / limit;
  if (ratio > 1) return { result: "异常", currClass: "text-red-400", tag: "tag-red" };
  if (ratio >= 0.8) return { result: "趋近", currClass: "text-orange-400", tag: "tag-org" };
  if (ratio >= 0.5) return { result: "关注", currClass: "text-yellow-400", tag: "tag-yel" };
  return { result: "正常", currClass: "text-green-400", tag: "tag-grn" };
};

const thresholds = computed(() => {
  const g = latest.value?.gases;
  if (!g) {
    // 未加载:显示占位(横线),不杜撰数值
    return [
      { gas: "H₂", threshold: "150 ppm", current: "—", currClass: "text-gray-500", result: "—", tag: "tag-gry" },
      { gas: "C₂H₂", threshold: "5 ppm", current: "—", currClass: "text-gray-500", result: "—", tag: "tag-gry" },
      { gas: "总烃", threshold: "150 ppm", current: "—", currClass: "text-gray-500", result: "—", tag: "tag-gry" },
      { gas: "CO", threshold: "300 ppm", current: "—", currClass: "text-gray-500", result: "—", tag: "tag-gry" },
    ];
  }
  const totalHc = g.ch4 + g.c2h4 + g.c2h6 + g.c2h2; // 总烃合成项(同后端口径)
  const rows = [
    { gas: "H₂", key: "h2", val: g.h2, limit: ATTENTION.h2 },
    { gas: "C₂H₂", key: "c2h2", val: g.c2h2, limit: ATTENTION.c2h2 },
    { gas: "总烃", key: "total_hydrocarbon", val: totalHc, limit: ATTENTION.total_hydrocarbon },
    { gas: "CO", key: "co", val: g.co, limit: ATTENTION.co },
  ];
  return rows.map((r) => ({
    gas: r.gas,
    threshold: `${r.limit} ppm`,
    current: r.val.toFixed(2),
    ...judge(r.val, r.limit),
  }));
});
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

/* 示意数据标签:右侧明细本周未接真实接口(Y2),待第 8 周联调 */
.demo-badge {
  font-size: 9px;
  font-weight: 500;
  color: #fcd34d;
  background: rgba(234, 179, 8, 0.12);
  border: 1px solid rgba(234, 179, 8, 0.35);
  padding: 1px 6px;
  border-radius: 10px;
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
