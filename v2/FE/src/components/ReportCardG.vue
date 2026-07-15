<script setup>
/**
 * DL/T 722-2014 附录 G 表 G.1 / 表 G.2 档案卡片
 * 有值如实填; null →「—」;合成缺字段不杜撰
 * 分析意见内【n】→ StdCite 角标(依据由规则绑死)
 */
import { computed } from 'vue'
import StdCite from '@/components/StdCite.vue'

const props = defineProps({
  g1: { type: Object, required: true },
  g2: { type: Object, default: null },
  /** compact: 页面预览缩略; full: 弹层完整表 */
  mode: { type: String, default: 'full' },
  /** 是否附带表 G.2 */
  showG2: { type: Boolean, default: true },
  /** 可选覆盖;默认用 g1.cite_map */
  citeMap: { type: Array, default: null },
  /** 分析意见是否展示【n】角标；报告内默认不展示 */
  showCites: { type: Boolean, default: false },
})

const np = computed(() => props.g1?.nameplate || {})
const sample = computed(() => props.g1?.sample || {})
const gases = computed(() => props.g1?.gases || {})

const citeByN = computed(() => {
  const list = props.citeMap || props.g1?.cite_map || []
  const m = {}
  for (const c of list) {
    if (c && c.n != null && c.id) m[Number(c.n)] = c
  }
  return m
})

/** 把「……【1】【2】……」拆成文本 + 角标片段；showCites=false 时去掉角标 */
const opinionParts = computed(() => {
  let text = props.g1?.opinion
  if (text == null || text === '') return [{ type: 'empty' }]
  if (!props.showCites) {
    text = String(text).replace(/【\d+】/g, '').replace(/\n{3,}/g, '\n\n').trim()
    return text ? [{ type: 'text', text }] : [{ type: 'empty' }]
  }
  const parts = []
  const re = /【(\d+)】/g
  let last = 0
  let m
  while ((m = re.exec(text))) {
    if (m.index > last) parts.push({ type: 'text', text: text.slice(last, m.index) })
    const n = Number(m[1])
    const hit = citeByN.value[n]
    if (hit) parts.push({ type: 'cite', n, id: hit.id })
    else parts.push({ type: 'text', text: m[0] })
    last = m.index + m[0].length
  }
  if (last < text.length) parts.push({ type: 'text', text: text.slice(last) })
  return parts.length ? parts : [{ type: 'text', text: String(text) }]
})

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
            <div class="opinion-body">
              <template v-for="(p, i) in opinionParts" :key="'op'+i">
                <span v-if="p.type === 'empty'">—</span>
                <span v-else-if="p.type === 'text'">{{ p.text }}</span>
                <div
                  v-else-if="p.type === 'cite'"
                  class="opinion-cite-line"
                >
                  <StdCite
                    class="opinion-cite"
                    :ref-id="p.id"
                    inline
                  />
                </div>
              </template>
            </div>
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
      <div class="g2-title">档案卡片（续）</div>
      <table class="g2-table">
        <tr>
          <td class="g2-lbl">其他检查性试验</td>
          <td class="g2-val" :class="{ empty: !g2.other_tests }">
            <div class="g2-ot-prose">{{ cell(g2.other_tests) }}</div>
          </td>
        </tr>
        <tr v-if="g2.maintenance || mode === 'full'">
          <td class="g2-lbl">检修情况</td>
          <td class="g2-val" :class="{ empty: !g2.maintenance }">{{ cell(g2.maintenance) }}</td>
        </tr>
        <tr v-if="g2.fault_records || mode === 'full'">
          <td class="g2-lbl">故障记录</td>
          <td class="g2-val" :class="{ empty: !g2.fault_records }">{{ cell(g2.fault_records) }}</td>
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
  min-height: 0;
  vertical-align: top;
}
.opinion-body { white-space: pre-wrap; }
.opinion-cite-line {
  display: block;
  margin-top: 2px;
  line-height: 1.4;
}
.opinion-cite :deep(.std-cite) {
  font-family: "Menlo", "Consolas", monospace;
  font-size: 10px;
  color: #0f766e;
  border-bottom-color: #0f766e;
  font-weight: 700;
  vertical-align: baseline;
}
.g1-foot-note {
  margin: 6px 10px 8px;
  font-size: 10px;
  color: #666;
  font-family: system-ui, sans-serif;
  line-height: 1.4;
}

.g2-lbl { width: 22%; }
.g2-val { min-height: 0; vertical-align: top; text-align: left; }
.g2-ot-prose {
  white-space: pre-wrap;
  line-height: 1.55;
  text-align: left;
}

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
