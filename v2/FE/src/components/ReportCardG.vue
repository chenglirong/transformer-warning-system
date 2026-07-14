<script setup>
/**
 * DL/T 722-2014 附录 G 表 G.1 / 表 G.2 档案卡片
 * 有值如实填; null →「—」;合成缺字段不杜撰
 */
import { computed } from 'vue'

const props = defineProps({
  g1: { type: Object, required: true },
  g2: { type: Object, default: null },
  /** compact: 页面预览缩略; full: 弹层完整表 */
  mode: { type: String, default: 'full' },
  /** 是否附带表 G.2 */
  showG2: { type: Boolean, default: true },
})

const np = computed(() => props.g1?.nameplate || {})
const sample = computed(() => props.g1?.sample || {})
const gases = computed(() => props.g1?.gases || {})

function cell(v) {
  return v == null || v === '' ? '—' : v
}

function gasTone(gas, v) {
  if (v == null) return 'empty'
  if (gas === 'c2h2') {
    if (v >= 5) return 'over'
    if (v >= 1) return 'warn'
  }
  if (gas === 'h2' || gas === 'thc') {
    if (v >= 150) return 'warn'
  }
  return ''
}

function col(arr, i) {
  return Array.isArray(arr) ? arr[i] : null
}

const GAS_ROWS = [
  { key: 'h2', label: 'H₂' },
  { key: 'o2', label: 'O₂' },
  { key: 'n2', label: 'N₂' },
  { key: 'co', label: 'CO' },
  { key: 'co2', label: 'CO₂' },
  { key: 'ch4', label: 'CH₄' },
  { key: 'c2h4', label: 'C₂H₄' },
  { key: 'c2h6', label: 'C₂H₆' },
  { key: 'c2h2', label: 'C₂H₂' },
  { key: 'thc', label: 'C₁+C₂' },
]
</script>

<template>
  <div class="rcg" :class="mode">
    <!-- 表 G.1 -->
    <div class="g1-sheet">
      <div class="g1-title">表 G.1 油中溶解气体分析档案卡片</div>
      <div class="g1-meta">
        <div class="g1-meta-left">
          <span class="g1-meta-line">{{ g1.bureau || '' }}</span>局（厂、所）
        </div>
        <div class="g1-meta-right">
          编号：<span class="g1-meta-no">{{ cell(g1.report_no) }}</span>
        </div>
      </div>

      <table class="g1-table">
        <!-- 铭牌行 1 -->
        <tr>
          <td class="g1-lbl">型号</td>
          <td class="g1-val empty" colspan="2">{{ cell(np.model) }}</td>
          <td class="g1-lbl">电压等级/容量</td>
          <td class="g1-val" colspan="2">{{ cell(np.voltage_capacity || g1.voltage) }}</td>
          <td class="g1-lbl">油重, t</td>
          <td class="g1-val empty">{{ cell(np.oil_weight_t) }}</td>
          <td class="g1-lbl">油种</td>
          <td class="g1-val empty">{{ cell(np.oil_type) }}</td>
        </tr>
        <!-- 铭牌行 2 -->
        <tr>
          <td class="g1-lbl">制造厂</td>
          <td class="g1-val empty" colspan="2">{{ cell(np.manufacturer) }}</td>
          <td class="g1-lbl">出厂序号</td>
          <td class="g1-val" colspan="2">{{ cell(np.serial_no || g1.device_id) }}</td>
          <td class="g1-lbl">出厂年月</td>
          <td class="g1-val empty">{{ cell(np.manufacture_date) }}</td>
          <td class="g1-lbl">投运日期</td>
          <td class="g1-val empty">{{ cell(np.commission_date) }}</td>
        </tr>
        <!-- 铭牌行 3 -->
        <tr>
          <td class="g1-lbl">冷却方式</td>
          <td class="g1-val empty" colspan="3">{{ cell(np.cooling) }}</td>
          <td class="g1-lbl">调压方式</td>
          <td class="g1-val empty" colspan="2">{{ cell(np.tap_changer) }}</td>
          <td class="g1-lbl">油保护方式</td>
          <td class="g1-val empty" colspan="2">{{ cell(np.oil_protection) }}</td>
        </tr>

        <!-- 取样条件 -->
        <tr>
          <td class="g1-section" rowspan="5">取样条件</td>
          <td class="g1-sub">年、月、日、时</td>
          <td
            v-for="i in 4"
            :key="'d'+i"
            class="g1-val"
            :class="{ empty: !col(sample.dates || g1.sample_dates, i - 1) }"
            colspan="2"
          >
            {{ cell(col(sample.dates || g1.sample_dates, i - 1)) }}
          </td>
        </tr>
        <tr>
          <td class="g1-sub">取样原因</td>
          <td
            v-for="i in 4"
            :key="'r'+i"
            class="g1-val empty"
            colspan="2"
          >{{ cell(col(sample.reason, i - 1)) }}</td>
        </tr>
        <tr>
          <td class="g1-sub">取样部位</td>
          <td
            v-for="i in 4"
            :key="'s'+i"
            class="g1-val empty"
            colspan="2"
          >{{ cell(col(sample.site, i - 1)) }}</td>
        </tr>
        <tr>
          <td class="g1-sub">油温, ℃</td>
          <td
            v-for="i in 4"
            :key="'t'+i"
            class="g1-val empty"
            colspan="2"
          >{{ cell(col(sample.oil_temp_c, i - 1)) }}</td>
        </tr>
        <tr>
          <td class="g1-sub">负荷, MVA</td>
          <td
            v-for="i in 4"
            :key="'l'+i"
            class="g1-val empty"
            colspan="2"
          >{{ cell(col(sample.load_mva, i - 1)) }}</td>
        </tr>

        <!-- 含气量 + 组分 -->
        <tr>
          <td class="g1-section" :rowspan="GAS_ROWS.length + 1">组分含量<br>μL/L</td>
          <td class="g1-sub">含气量, %</td>
          <td
            v-for="i in 4"
            :key="'gc'+i"
            class="g1-val empty"
            colspan="2"
          >{{ cell(col(g1.gas_content_pct, i - 1)) }}</td>
        </tr>
        <tr v-for="row in GAS_ROWS" :key="row.key">
          <td class="g1-sub">{{ row.label }}</td>
          <td
            v-for="i in 4"
            :key="row.key + i"
            class="g1-val"
            :class="gasTone(row.key, col(gases[row.key], i - 1)) || (col(gases[row.key], i - 1) == null ? 'empty' : '')"
            colspan="2"
          >
            {{ cell(col(gases[row.key], i - 1)) }}
          </td>
        </tr>

        <!-- 速率区 -->
        <tr>
          <td class="g1-sub" colspan="2">总烃增长, μL/L</td>
          <td
            v-for="i in 4"
            :key="'tg'+i"
            class="g1-val"
            :class="{ empty: col(g1.thc_growth, i - 1) == null }"
            colspan="2"
          >{{ cell(col(g1.thc_growth, i - 1)) }}</td>
        </tr>
        <tr>
          <td class="g1-sub" colspan="2">实际运行时间, 天</td>
          <td
            v-for="i in 4"
            :key="'rd'+i"
            class="g1-val"
            :class="{ empty: col(g1.run_days, i - 1) == null }"
            colspan="2"
          >{{ cell(col(g1.run_days, i - 1)) }}</td>
        </tr>
        <tr>
          <td class="g1-sub" colspan="2">总烃产气率, mL/天</td>
          <td
            v-for="i in 4"
            :key="'gr'+i"
            class="g1-val empty"
            colspan="2"
          >{{ cell(col(g1.thc_gassing_rate_ml_d, i - 1)) }}</td>
        </tr>
        <tr>
          <td class="g1-sub" colspan="2">试验报告编号</td>
          <td
            v-for="i in 4"
            :key="'tn'+i"
            class="g1-val"
            :class="{ empty: !col(g1.test_report_nos, i - 1) }"
            colspan="2"
          >{{ cell(col(g1.test_report_nos, i - 1)) }}</td>
        </tr>
        <tr>
          <td class="g1-sub" colspan="2">分析意见</td>
          <td class="g1-opinion" colspan="8">
            <div>{{ cell(g1.opinion) }}</div>
          </td>
        </tr>
      </table>

      <p v-if="g1.empty_note || g1.thc_gassing_rate_note" class="g1-foot-note">
        {{ g1.empty_note }}
        <template v-if="g1.thc_gassing_rate_note"> · {{ g1.thc_gassing_rate_note }}</template>
      </p>
    </div>

    <!-- 表 G.2 -->
    <div v-if="showG2 && g2" class="g2-sheet">
      <div class="g2-title">表 G.2 油中溶解气体分析档案卡片</div>
      <table class="g2-table">
        <tr>
          <td class="g2-lbl">其他检查性试验</td>
          <td class="g2-val empty">{{ cell(g2.other_tests) }}</td>
        </tr>
        <tr>
          <td class="g2-lbl">检修情况</td>
          <td class="g2-val empty">{{ cell(g2.maintenance) }}</td>
        </tr>
        <tr>
          <td class="g2-lbl">故障记录</td>
          <td class="g2-val empty">{{ cell(g2.fault_records) }}</td>
        </tr>
      </table>
      <p v-if="g2.note" class="g1-foot-note">{{ g2.note }}</p>
    </div>
  </div>
</template>

<style scoped>
.rcg {
  font-family: "Songti SC", "SimSun", "Noto Serif SC", serif;
  color: #111;
  background: #fff;
}

.g1-sheet, .g2-sheet {
  border: 2px solid #111;
  background: #fff;
}
.g2-sheet { margin-top: 16px; }

.g1-title, .g2-title {
  text-align: center;
  font-weight: 700;
  font-size: 15px;
  letter-spacing: 2px;
  padding: 8px 10px 4px;
}
.g1-meta {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding: 2px 12px 6px;
  font-size: 12px;
}
.g1-meta-no {
  display: inline-block;
  min-width: 110px;
  border-bottom: 1px solid #111;
  text-align: center;
  font-family: "Menlo", "Consolas", monospace;
  font-size: 11px;
}
.g1-meta-line {
  display: inline-block;
  min-width: 96px;
  border-bottom: 1px solid #111;
  margin-right: 2px;
  text-align: center;
}

.g1-table, .g2-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
.g1-table td, .g2-table td {
  border: 1px solid #111;
  padding: 3px 5px;
  font-size: 11px;
  line-height: 1.35;
  vertical-align: middle;
  word-break: break-all;
}
.g1-lbl, .g1-sub, .g1-section, .g2-lbl {
  background: #fafafa;
  font-weight: 600;
  text-align: center;
  white-space: nowrap;
}
.g1-section {
  writing-mode: vertical-rl;
  letter-spacing: 2px;
  width: 28px;
  padding: 6px 2px;
}
.g1-val.empty, .g2-val.empty { color: #888; }
.g1-val.warn { color: #b45309; font-weight: 700; }
.g1-val.over { color: #b91c1c; font-weight: 700; }
.g1-opinion {
  font-size: 11px;
  line-height: 1.55;
  text-align: left;
  min-height: 72px;
  vertical-align: top;
}
.g1-foot-note {
  margin: 6px 10px 8px;
  font-size: 10px;
  color: #666;
  font-family: system-ui, sans-serif;
  line-height: 1.4;
}

.g2-lbl { width: 22%; }
.g2-val { min-height: 48px; vertical-align: top; text-align: left; }

/* 预览缩略 */
.rcg.compact .g1-title,
.rcg.compact .g2-title { font-size: 12px; letter-spacing: 1px; padding: 5px; }
.rcg.compact .g1-meta { font-size: 10px; padding: 2px 6px 4px; }
.rcg.compact .g1-table td,
.rcg.compact .g2-table td { font-size: 9px; padding: 1px 3px; }
.rcg.compact .g1-opinion { font-size: 9px; min-height: 40px; }
.rcg.compact .g1-section { width: 18px; letter-spacing: 1px; }
.rcg.compact .g2-sheet { margin-top: 8px; }
.rcg.compact .g1-foot-note { font-size: 9px; margin: 4px 6px; }
</style>
