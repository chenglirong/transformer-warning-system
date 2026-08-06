<script setup>
/**
 * DL/T 722-2014 附录 G 表 G.1 / 表 G.2 档案卡片
 * 有值如实填; null →「—」;合成缺字段不杜撰
 * 报告正文不挂条款角标;化学式一律走 <sub> 排版,不用 Unicode 下标(报告宋体缺字会裂开)
 */
import { computed } from 'vue'
import { downloadReportFile } from '@/utils/reportDownload'

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

const SUB_DIGITS = '₀₁₂₃₄₅₆₇₈₉'

/** 文本按 Unicode 下标切片 → 正文段 + <sub> 段 */
function subParts(text) {
  const out = []
  let buf = ''
  for (const ch of String(text)) {
    const i = SUB_DIGITS.indexOf(ch)
    if (i >= 0) {
      if (buf) out.push({ sub: false, text: buf })
      buf = ''
      const last = out[out.length - 1]
      if (last && last.sub) last.text += String(i)
      else out.push({ sub: true, text: String(i) })
    } else {
      buf += ch
    }
  }
  if (buf) out.push({ sub: false, text: buf })
  return out
}

/** 化学式串(如 C2H4、C1+C2)→ 字母段 + <sub> 数字段 */
function formulaParts(formula) {
  return (String(formula).match(/[A-Za-z]+|\d+|./g) || []).map((tok) => ({
    sub: /^\d+$/.test(tok),
    text: tok,
  }))
}

const opinionParts = computed(() => {
  const text = String(props.g1?.opinion ?? '')
    .replace(/【\d+】/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
  return text ? subParts(text) : null
})

const otherTestsParts = computed(() => {
  const text = String(props.g2?.other_tests ?? '').trim()
  return text ? subParts(text) : null
})

function cell(v) {
  return v == null || v === '' ? '—' : v
}

function col(arr, i) {
  return Array.isArray(arr) ? arr[i] : null
}

async function downloadPdf() {
  await downloadReportFile('pdf', { g1: props.g1, g2: props.g2 })
}

defineExpose({ downloadPdf })

const GAS_ROWS = [
  { key: 'h2', formula: 'H2' },
  { key: 'o2', formula: 'O2' },
  { key: 'n2', formula: 'N2' },
  { key: 'co', formula: 'CO' },
  { key: 'co2', formula: 'CO2' },
  { key: 'ch4', formula: 'CH4' },
  { key: 'c2h4', formula: 'C2H4' },
  { key: 'c2h6', formula: 'C2H6' },
  { key: 'c2h2', formula: 'C2H2' },
  { key: 'thc', formula: 'C1+C2' },
]

const footNote = computed(() => {
  const parts = [
    np.value?.nameplate_note,
    props.g1?.empty_note,
    props.g1?.thc_gassing_rate_note,
    props.showG2 ? props.g2?.note : null,
  ]
  return parts.filter(Boolean).join(' · ')
})
</script>

<template>
  <div class="rcg" :class="mode">
    <div class="g1-sheet">
      <div class="g1-title">油中溶解气体分析档案卡片</div>
      <div class="g1-meta">
        <div class="g1-meta-left">
          <span class="g1-meta-line">{{ g1.bureau || '' }}</span>局（厂、所）
        </div>
        <div class="g1-meta-right">
          报告编号：<span class="g1-meta-no">{{ cell(g1.report_no) }}</span>
        </div>
      </div>

      <table class="g1-table">
        <tbody>
        <!-- 铭牌行 1 -->
        <tr>
          <td class="g1-lbl">型号</td>
          <td class="g1-val" colspan="2" :class="{ empty: !np.model }">{{ cell(np.model) }}</td>
          <td class="g1-lbl">电压等级/容量</td>
          <td class="g1-val" colspan="2" :class="{ empty: !(np.voltage_capacity || g1.voltage) }">{{ cell(np.voltage_capacity || g1.voltage) }}</td>
          <td class="g1-lbl">油重, t</td>
          <td class="g1-val" :class="{ empty: np.oil_weight_t == null || np.oil_weight_t === '' }">{{ cell(np.oil_weight_t) }}</td>
          <td class="g1-lbl">油种</td>
          <td class="g1-val" :class="{ empty: !np.oil_type }">{{ cell(np.oil_type) }}</td>
        </tr>
        <!-- 铭牌行 2 -->
        <tr>
          <td class="g1-lbl">制造厂</td>
          <td class="g1-val" colspan="2" :class="{ empty: !np.manufacturer }">{{ cell(np.manufacturer) }}</td>
          <td class="g1-lbl">出厂序号</td>
          <td class="g1-val" colspan="2" :class="{ empty: !(np.serial_no || g1.device_id) }">{{ cell(np.serial_no || g1.device_id) }}</td>
          <td class="g1-lbl">出厂年月</td>
          <td class="g1-val" :class="{ empty: !np.manufacture_date }">{{ cell(np.manufacture_date) }}</td>
          <td class="g1-lbl">投运日期</td>
          <td class="g1-val" :class="{ empty: !np.commission_date }">{{ cell(np.commission_date) }}</td>
        </tr>
        <!-- 铭牌行 3：三组，前两组对齐上行「型号/电压」列界，油保护占右侧两格 -->
        <tr>
          <td class="g1-lbl">冷却方式</td>
          <td class="g1-val" colspan="2" :class="{ empty: !np.cooling }">{{ cell(np.cooling) }}</td>
          <td class="g1-lbl">调压方式</td>
          <td class="g1-val" colspan="2" :class="{ empty: !np.tap_changer }">{{ cell(np.tap_changer) }}</td>
          <td class="g1-lbl">油保护方式</td>
          <td class="g1-val" colspan="3" :class="{ empty: !np.oil_protection }">{{ cell(np.oil_protection) }}</td>
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
          <td class="g1-sub">
            <span v-for="(p, k) in formulaParts(row.formula)" :key="k">
              <sub v-if="p.sub">{{ p.text }}</sub>
              <template v-else>{{ p.text }}</template>
            </span>
          </td>
          <td
            v-for="i in 4"
            :key="row.key + i"
            class="g1-val"
            :class="{ empty: col(gases[row.key], i - 1) == null }"
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
          <td class="g1-sub" colspan="2">总烃绝对产气速率, mL/天</td>
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
            <div class="opinion-body">
              <span v-if="!opinionParts">—</span>
              <span v-for="(p, i) in opinionParts || []" :key="'op'+i">
                <sub v-if="p.sub">{{ p.text }}</sub>
                <template v-else>{{ p.text }}</template>
              </span>
            </div>
          </td>
        </tr>

        <!-- 表 G.2 栏并入同一张表 -->
        <template v-if="showG2 && g2">
          <tr>
            <td class="g1-lbl" colspan="2">其他检查性试验</td>
            <td class="g1-val g2-ot" colspan="8" :class="{ empty: !g2.other_tests }">
              <div class="g2-ot-prose">
                <span v-if="!otherTestsParts">—</span>
                <span v-for="(p, i) in otherTestsParts || []" :key="'ot'+i">
                  <sub v-if="p.sub">{{ p.text }}</sub>
                  <template v-else>{{ p.text }}</template>
                </span>
              </div>
            </td>
          </tr>
          <tr>
            <td class="g1-lbl" colspan="2">检修情况</td>
            <td class="g1-val" colspan="8" :class="{ empty: !g2.maintenance }">{{ cell(g2.maintenance) }}</td>
          </tr>
          <tr>
            <td class="g1-lbl" colspan="2">故障记录</td>
            <td class="g1-val" colspan="8" :class="{ empty: !g2.fault_records }">{{ cell(g2.fault_records) }}</td>
          </tr>
        </template>
        </tbody>
      </table>

      <p v-if="footNote" class="g1-foot-note">{{ footNote }}</p>
    </div>
  </div>
</template>

<style scoped>
.rcg {
  font-family: "Songti SC", "SimSun", "Noto Serif SC", serif;
  color: #111;
  background: #fff;
}

.g1-sheet {
  border: 2px solid #111;
  background: #fff;
}

.g1-title {
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

.g1-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
.g1-table td {
  border: 1px solid #111;
  padding: 3px 5px;
  font-size: 11px;
  line-height: 1.35;
  vertical-align: middle;
  word-break: break-all;
}
.g1-lbl, .g1-sub, .g1-section {
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
.g1-val.empty { color: #888; }
.g1-opinion {
  font-size: 11px;
  line-height: 1.55;
  text-align: left;
  min-height: 0;
  vertical-align: top;
}
.opinion-body { white-space: pre-wrap; }
.rcg sub {
  font-size: 0.72em;
  line-height: 0;
  vertical-align: -0.22em;
}
.g1-foot-note {
  margin: 6px 10px 8px;
  font-size: 10px;
  color: #666;
  font-family: system-ui, sans-serif;
  line-height: 1.4;
}

.g2-ot { vertical-align: top; text-align: left; }
.g2-ot-prose {
  white-space: pre-wrap;
  line-height: 1.55;
  text-align: left;
}

/* 预览缩略 */
.rcg.compact .g1-title { font-size: 12px; letter-spacing: 1px; padding: 5px; }
.rcg.compact .g1-meta { font-size: 10px; padding: 2px 6px 4px; }
.rcg.compact .g1-table td { font-size: 9px; padding: 1px 3px; }
.rcg.compact .g1-opinion { font-size: 9px; min-height: 40px; }
.rcg.compact .g1-section { width: 18px; letter-spacing: 1px; }
.rcg.compact .g1-foot-note { font-size: 9px; margin: 4px 6px; }
</style>
