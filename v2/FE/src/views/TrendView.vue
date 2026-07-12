<script setup>
// 趋势预警页:DL/T 722 §9.3.2 相对产气速率(%/月)逐日走势 + 「预」点。
// 口径(D-004):722 §9.3.2 相对速率(月环比+连续3天确认),与检测②处置/④预同尺;
// 落档另用 1498.2 表A.3 %/周,不在本页。
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'
import http from '@/service/http'

const loading = ref(true)
const summary = ref({})
const preEvents = ref([])
const thcAttention = ref(10)
const rateEl = ref(null)

function renderRate(series) {
  const chart = echarts.init(rateEl.value)
  const days = series.map((s) => s.day)
  const rate = series.map((s) => s.rel_rate)
  const preScatter = series.filter((s) => s.is_pre).map((s) => [s.day, s.rel_rate])
  // 首次浓度超标日(档位首次进注意值1+)——竖线,对齐参考图
  const firstOver = series.find((s) => s.grade && s.grade !== '正常')
  chart.setOption({
    title: { text: '360 天总烃相对产气速率走势(%/月,月环比)', left: 'center',
      textStyle: { fontSize: 14 } },
    tooltip: {
      trigger: 'axis',
      formatter: (ps) => {
        const s = series[ps[0].dataIndex]
        const pre = s.is_pre ? '<br/><b style="color:#dc2626">「预」浓度未超但速率连续超10%/月</b>' : ''
        return `第 ${s.day} 天(${s.date})<br/>相对速率:${s.rel_rate ?? '—'} %/月<br/>档位:${s.grade}${pre}`
      },
    },
    legend: { data: ['相对产气速率(总烃)', '「预」触发点'], top: 28 },
    grid: { left: 66, right: 40, top: 62, bottom: 70 },
    xAxis: { type: 'category', data: days, name: '天数', boundaryGap: false },
    yAxis: { type: 'value', name: '相对产气速率(%/月)' },
    // 全局看爬坡全貌 + 拖动放大到低区间看清 10%/月 注意线和「预」点
    dataZoom: [
      { type: 'inside' },
      { type: 'slider', bottom: 8, height: 18, start: 0, end: 100 },
    ],
    series: [
      {
        name: '相对产气速率(总烃)', type: 'line', data: rate,
        showSymbol: false, lineStyle: { color: '#2563eb', width: 1.2 },
        markLine: {
          symbol: 'none', silent: true,
          data: [
            { yAxis: thcAttention.value, lineStyle: { color: '#f59e0b', type: 'dashed' },
              label: { formatter: '10%/月 注意线', color: '#f59e0b', position: 'end' } },
            ...(firstOver ? [{ xAxis: firstOver.day,
              lineStyle: { color: '#10b981', type: 'dashed' },
              label: { formatter: `首次浓度超标\n第${firstOver.day}天`, color: '#10b981' } }] : []),
          ],
        },
      },
      {
        name: '「预」触发点', type: 'scatter', data: preScatter,
        symbolSize: 11, itemStyle: { color: '#dc2626' }, z: 5,
      },
    ],
  })
}

onMounted(async () => {
  try {
    const res = await http.get('/trend/daily')
    summary.value = res.summary
    preEvents.value = res.pre_events
    thcAttention.value = res.thc_attention
    renderRate(res.series)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div v-loading="loading" class="trend">
    <div class="head">
      <h2>产气趋势预警(全程 360 天)</h2>
      <p class="sub">气体涨得快不快?有没有「还没超标但涨势已异常」的情况需要提前预警?</p>
    </div>

    <div class="kpis">
      <div class="kpi">
        <div class="kpi-label">当前总烃相对产气速率</div>
        <div class="kpi-val blue">{{ summary.latest_rate ?? '—' }} <span>%/月</span></div>
        <div class="kpi-sub">第 {{ summary.latest_day ?? '—' }} 天</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">「预」事件总数</div>
        <div class="kpi-val orange">{{ summary.pre_count ?? 0 }} <span>次</span></div>
        <div class="kpi-sub">浓度未超但速率连续超 10%/月</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">首次浓度超标日</div>
        <div class="kpi-val purple">第 {{ summary.first_over_day ?? '—' }} 天</div>
        <div class="kpi-sub">{{ summary.first_over_date ?? '' }}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">监测总天数</div>
        <div class="kpi-val green">{{ summary.total_days ?? '—' }} <span>天</span></div>
        <div class="kpi-sub">合成单台 × 360 天</div>
      </div>
    </div>

    <div ref="rateEl" class="chart"></div>

    <!-- 「预」事件明细表(浓度未超但速率连续超注意值) -->
    <div class="panel">
      <div class="panel-head">
        <div class="panel-title">「预」事件明细表(浓度未超注意值2,但相对速率连续超 10%/月)</div>
        <el-tooltip placement="top-end" effect="light" :show-after="100">
          <template #content>
            <div class="calc-tip">
              <b>相对产气速率(式2,本报告采用)</b><br/>
              γᵣ =(C₂ − C₁)/ C₁ × 1/Δt × 100%<br/>
              C₂/C₁=后/前次浓度、Δt=间隔(月);本页取月环比(今 vs 30 天前,Δt=1 月)得 %/月,
              总烃注意值 10%/月、总烃<10μL/L 不宜用。<br/>
              <b>绝对产气速率(式1)</b>需油量/油密度,合成数据无,不计算。
            </div>
          </template>
          <span class="calc-toggle">产气速率计算方法 ⓘ</span>
        </el-tooltip>
      </div>
      <el-table :data="preEvents" border stripe empty-text="无「预」事件">
        <el-table-column type="index" label="序号" width="64" />
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column prop="day" label="第几天" width="84" />
        <el-table-column prop="grade" label="当日档位" width="96" />
        <el-table-column prop="total_hydrocarbon" label="总烃(μL/L)" width="110" />
        <el-table-column prop="rel_rate" label="相对速率(%/月)" width="130">
          <template #default="{ row }">
            <span class="rate-hot">{{ row.rel_rate?.toFixed(1) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="basis" label="命中判据" min-width="220" />
        <el-table-column prop="advice" label="建议" min-width="160" />
      </el-table>
    </div>

    <div class="note">
      口径(D-004):DL/T 722 §9.3.2 相对产气速率(%/月,月环比 + 连续3天确认);
      「预」= 浓度未超注意值但速率连续超 10%/月 →§9.3.3 a) 缩短检测周期。
      落档另用 DL/T 1498.2 表A.3(%/周),不在本页。异常段速率爬坡幅度大,拖动图下滑块可放大看清 10%/月 注意线与「预」点。
    </div>
  </div>
</template>

<style scoped>
.trend { display: flex; flex-direction: column; gap: 16px; }
.head h2 { margin: 0 0 4px; font-size: 18px; }
.sub { margin: 0; color: #6b7280; font-size: 13px; }
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.kpi { background: #fff; border-radius: 8px; padding: 14px 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.kpi-label { color: #374151; font-size: 14px; }
.kpi-val { font-size: 28px; font-weight: 700; margin: 4px 0; }
.kpi-val span { font-size: 14px; font-weight: 400; color: #6b7280; }
.kpi-val.blue { color: #2563eb; } .kpi-val.green { color: #10b981; }
.kpi-val.orange { color: #f59e0b; } .kpi-val.purple { color: #7c3aed; }
.kpi-sub { color: #6b7280; font-size: 13px; }
.chart { width: 100%; height: 420px; background: #fff; border-radius: 8px;
  padding: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.panel { background: #fff; border-radius: 8px; padding: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.panel-head { display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 12px; }
.panel-title { font-size: 15px; font-weight: 600; }
.calc-toggle { font-size: 13px; color: #2563eb; cursor: pointer; user-select: none; }
.calc-tip { max-width: 340px; font-size: 13px; line-height: 1.7; }
.rate-hot { color: #dc2626; font-weight: 600; }
.note { color: #4b5563; font-size: 13px; line-height: 1.7; }
:deep(.el-table) { font-size: 13px; }
</style>
