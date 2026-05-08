<template>
  <div class="h-screen flex flex-col">
    <AppHeader
      title="预 警 操 作 管 理 中 心"
      icon="mdi:clipboard-list"
      subtitle="全生命周期工单"
    />

    <section class="px-3 pt-3 grid grid-cols-5 gap-3">
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">紧急工单</p>
            <p class="text-2xl font-bold text-red-400">2<span class="text-xs ml-1">条</span></p>
          </div>
          <iconify-icon class="text-3xl text-red-400 pulse" icon="mdi:alert-octagon"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">1 处置中 · 1 待响应</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">重要工单</p>
            <p class="text-2xl font-bold text-orange-400">5<span class="text-xs ml-1">条</span></p>
          </div>
          <iconify-icon class="text-3xl text-orange-400" icon="mdi:alert"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">4 处置中 · 平均 22min</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">一般 / 提示</p>
            <p class="text-2xl font-bold text-yellow-400">13<span class="text-xs ml-1">条</span></p>
          </div>
          <iconify-icon class="text-3xl text-yellow-400" icon="mdi:bell"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">一般 9 · 提示 4</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">今日闭环</p>
            <p class="text-2xl font-bold text-green-400">28<span class="text-xs ml-1">条</span></p>
          </div>
          <iconify-icon class="text-3xl text-green-400" icon="mdi:check-decagram"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">自动处置占 73%</p>
      </KpiCard>
      <KpiCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[11px] text-gray-400">平均响应</p>
            <p class="text-2xl font-bold text-cyan-400">14<span class="text-xs ml-1">min</span></p>
          </div>
          <iconify-icon class="text-3xl text-cyan-400" icon="mdi:timer-sand"></iconify-icon>
        </div>
        <p class="text-[10px] text-gray-500 mt-1">SLA 30 min · 达标 96.4%</p>
      </KpiCard>
    </section>

    <main class="flex-1 grid grid-cols-12 gap-3 p-3 overflow-hidden" style="min-height: 0">
      <!-- Ticket list -->
      <div class="col-span-8 glass rounded-lg p-3 flex flex-col overflow-hidden">
        <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2 flex items-center justify-between">
          <span><iconify-icon icon="mdi:table-large"></iconify-icon> 预警工单列表（按风险等级降序）</span>
          <div class="flex gap-2 text-[11px]">
            <button class="btn btn-blue">全部 20</button>
            <button class="btn tag-red">紧急 2</button>
            <button class="btn tag-org">重要 5</button>
            <button class="btn tag-yel">一般 9</button>
            <button class="btn tag-blu">提示 4</button>
          </div>
        </h3>
        <div class="overflow-auto" style="height: calc(100% - 40px)">
          <table>
            <colgroup>
              <col style="width: 11%" />
              <col style="width: 8%" />
              <col style="width: 7%" />
              <col style="width: 12%" />
              <col style="width: 17%" />
              <col style="width: 25%" />
              <col style="width: 8%" />
              <col style="width: 7%" />
            </colgroup>
            <thead class="sticky top-0">
              <tr>
                <th>工单 ID</th>
                <th class="nowrap">时间</th>
                <th class="nowrap">等级</th>
                <th class="nowrap">设备 / 维度</th>
                <th>预警内容</th>
                <th>智能体处置建议</th>
                <th class="nowrap">状态</th>
                <th class="nowrap">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="t in tickets" :key="t.id">
                <td class="text-cyan-300 font-mono nowrap">{{ t.id }}</td>
                <td class="text-gray-400 nowrap">{{ t.time }}</td>
                <td><span class="px-2 py-0.5 rounded text-[10px]" :class="t.levelTag">{{ t.level }}</span></td>
                <td>{{ t.device }}</td>
                <td>{{ t.content }}</td>
                <td class="text-cyan-300/90 text-[11px]">{{ t.advice }}</td>
                <td><span class="px-2 py-0.5 rounded text-[10px]" :class="t.statusTag">{{ t.status }}</span></td>
                <td><button class="btn" :class="t.btnClass">{{ t.btn }}</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Right column: stats + pipeline -->
      <div class="col-span-4 flex flex-col gap-3 overflow-hidden">
        <div class="glass rounded-lg p-3 flex-1 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:chart-donut"></iconify-icon> 7 日预警等级分布 &amp; 维度来源
          </h3>
          <div class="grid grid-cols-2 gap-2" style="height: calc(100% - 28px)">
            <EChart :option="levelOption" />
            <EChart :option="dimOption" />
          </div>
        </div>

        <div class="glass rounded-lg p-3 flex-1 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:progress-clock"></iconify-icon> 平均处置时长（min）
          </h3>
          <div class="w-full" style="height: calc(100% - 28px)">
            <EChart :option="timeOption" />
          </div>
        </div>

        <div class="glass rounded-lg p-3 overflow-hidden">
          <h3 class="panel-title text-sm font-bold text-cyan-300 mb-2">
            <iconify-icon icon="mdi:pipe"></iconify-icon> 智能体处置流水线
          </h3>
          <div class="flex items-center justify-between text-[10px] text-gray-400 mb-2">
            <div class="flex items-center gap-1">
              <span class="w-2 h-2 bg-blue-500 rounded-full"></span>感知
            </div>
            <iconify-icon icon="mdi:arrow-right"></iconify-icon>
            <div class="flex items-center gap-1">
              <span class="w-2 h-2 bg-cyan-500 rounded-full"></span>研判
            </div>
            <iconify-icon icon="mdi:arrow-right"></iconify-icon>
            <div class="flex items-center gap-1">
              <span class="w-2 h-2 bg-purple-500 rounded-full"></span>派单
            </div>
            <iconify-icon icon="mdi:arrow-right"></iconify-icon>
            <div class="flex items-center gap-1">
              <span class="w-2 h-2 bg-green-500 rounded-full"></span>闭环
            </div>
          </div>
          <div class="grid grid-cols-4 gap-1 text-center text-[10px]">
            <div class="bg-blue-500/10 rounded p-1 border border-blue-500/30"><p class="text-blue-300 font-bold">48</p><p class="text-gray-500">条/日</p></div>
            <div class="bg-cyan-500/10 rounded p-1 border border-cyan-500/30"><p class="text-cyan-300 font-bold">44</p><p class="text-gray-500">条/日</p></div>
            <div class="bg-purple-500/10 rounded p-1 border border-purple-500/30"><p class="text-purple-300 font-bold">35</p><p class="text-gray-500">条/日</p></div>
            <div class="bg-green-500/10 rounded p-1 border border-green-500/30"><p class="text-green-300 font-bold">28</p><p class="text-gray-500">条/日</p></div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import AppHeader from '@/components/AppHeader.vue'
import KpiCard from '@/components/KpiCard.vue'
import EChart from '@/components/EChart.vue'
import { AXIS, TT } from '@/utils/chartDefaults'

const tickets = [
  { id: '#WO-20240424-0107', time: '10:42:15', level: '紧急', levelTag: 'tag-red', device: '#2主变 / DGA',       content: 'C₂H₂=3.24 ppm 72h ↑≥20%',          advice: '立即停运，开展油质检测和内部故障排查',           status: '处置中', statusTag: 'tag-org', btn: '详情', btnClass: 'btn-blue' },
  { id: '#WO-20240424-0106', time: '09:58:30', level: '紧急', levelTag: 'tag-red', device: '#5主变 / 电气',      content: '绕组温度 102℃ 逼近 105℃',           advice: '立即检查冷却系统，降低负载，持续升高则停运',     status: '待响应', statusTag: 'tag-red', btn: '详情', btnClass: 'btn-blue' },
  { id: '#WO-20240424-0105', time: '10:15:02', level: '重要', levelTag: 'tag-org', device: '#2主变 / 电气',      content: '局放量 88pC 趋近 100pC 阈值',        advice: '停运设备，开展局放定位检测，排查绝缘缺陷',        status: '处置中', statusTag: 'tag-org', btn: '详情', btnClass: 'btn-blue' },
  { id: '#WO-20240424-0104', time: '09:15:30', level: '重要', levelTag: 'tag-org', device: '#1主变 / 冷却辅助',  content: '油泵 P2 故障停机 + 电源中断',         advice: '立即检修故障油泵，恢复电源，冷却失效则停运',     status: '处置中', statusTag: 'tag-org', btn: '详情', btnClass: 'btn-blue' },
  { id: '#WO-20240424-0103', time: '08:20:11', level: '重要', levelTag: 'tag-org', device: '#7主变 / 机械结构',  content: 'A 套管 tanδ=0.48% 趋近 0.5%',       advice: '停运设备，检修套管，排查受潮、绝缘劣化',          status: '处置中', statusTag: 'tag-org', btn: '详情', btnClass: 'btn-blue' },
  { id: '#WO-20240424-0102', time: '08:50:44', level: '一般', levelTag: 'tag-yel', device: '#5主变 / 电气',      content: '负载电流 1.05 倍额定（长期）',        advice: '调整负载分配，降低过载电流，监测绕组温度',        status: '处置中', statusTag: 'tag-org', btn: '详情', btnClass: 'btn-blue' },
  { id: '#WO-20240424-0101', time: '07:22:10', level: '一般', levelTag: 'tag-yel', device: '#3主变 / 机械结构',  content: '油温-环境温差 28℃ 持续增大',          advice: '排查冷却系统，清理散热片灰尘，加强通风',          status: '处置中', statusTag: 'tag-org', btn: '详情', btnClass: 'btn-blue' },
  { id: '#WO-20240424-0100', time: '07:12:19', level: '一般', levelTag: 'tag-yel', device: '#4主变 / 电气',      content: '分接开关 12 次/日 高于历史均值',      advice: '核查电压波动，稳定运行电压，监测控制回路',        status: '已闭环', statusTag: 'tag-grn', btn: '回溯', btnClass: 'btn-grn' },
  { id: '#WO-20240424-0099', time: '06:45:20', level: '提示', levelTag: 'tag-blu', device: '环境工况',           content: '环境温度 38℃ 接近 40℃ 阈值',         advice: '采取降温措施，加强设备绝缘监测',                  status: '跟踪',   statusTag: 'tag-gry', btn: '详情', btnClass: 'btn-blue' },
  { id: '#WO-20240424-0098', time: '04:10:00', level: '提示', levelTag: 'tag-blu', device: '#9主变 / 机械结构',  content: '振动频率峰值偏移 +18%',               advice: '加强振动监测，排查设备基础松动',                  status: '跟踪',   statusTag: 'tag-gry', btn: '详情', btnClass: 'btn-blue' },
  { id: '#WO-20240424-0097', time: '02:45:00', level: '一般', levelTag: 'tag-yel', device: '#4主变 / 机械结构',  content: '油枕压力波动异常（环境温差联动）',    advice: '跟踪油位、压力变化，结合环境温度分析',            status: '已闭环', statusTag: 'tag-grn', btn: '回溯', btnClass: 'btn-grn' },
  { id: '#WO-20240424-0096', time: '01:20:00', level: '提示', levelTag: 'tag-blu', device: '智能体',             content: 'C₂H₂ 预警阈值自主优化 5.0 → 4.5 ppm', advice: '基于 SFP9-240000/220 + 17 年运行数据',          status: '已生效', statusTag: 'tag-grn', btn: '回溯', btnClass: 'btn-grn' }
]

const levelOption = {
  tooltip: { trigger: 'item', ...TT },
  title: { text: '等级', left: 'center', bottom: 0, textStyle: { color: '#9ca3af', fontSize: 10, fontWeight: 'normal' } },
  series: [{
    type: 'pie',
    radius: ['42%', '72%'],
    center: ['50%', '45%'],
    label: { color: '#cbd5e1', fontSize: 9, formatter: '{b}\n{c}' },
    data: [
      { value: 8,  name: '紧急', itemStyle: { color: '#ef4444' } },
      { value: 22, name: '重要', itemStyle: { color: '#f97316' } },
      { value: 58, name: '一般', itemStyle: { color: '#f59e0b' } },
      { value: 35, name: '提示', itemStyle: { color: '#3b82f6' } }
    ]
  }]
}

const dimOption = {
  tooltip: { trigger: 'item', ...TT },
  title: { text: '维度', left: 'center', bottom: 0, textStyle: { color: '#9ca3af', fontSize: 10, fontWeight: 'normal' } },
  series: [{
    type: 'pie',
    radius: ['42%', '72%'],
    center: ['50%', '45%'],
    label: { color: '#cbd5e1', fontSize: 9, formatter: '{b}\n{c}' },
    data: [
      { value: 32, name: '电气', itemStyle: { color: '#3b82f6' } },
      { value: 28, name: 'DGA',  itemStyle: { color: '#ef4444' } },
      { value: 24, name: '机械', itemStyle: { color: '#f59e0b' } },
      { value: 22, name: '冷却', itemStyle: { color: '#10b981' } },
      { value: 17, name: '环境', itemStyle: { color: '#06b6d4' } }
    ]
  }]
}

const timeOption = {
  tooltip: { trigger: 'axis', ...TT },
  grid: { top: 20, bottom: 20, left: 40, right: 10 },
  xAxis: { type: 'category', data: ['紧急', '重要', '一般', '提示'], ...AXIS },
  yAxis: { type: 'value', ...AXIS, name: 'min', nameTextStyle: { color: '#9ca3af', fontSize: 10 } },
  series: [{
    type: 'bar',
    data: [
      { value: 8,  itemStyle: { color: '#ef4444' } },
      { value: 22, itemStyle: { color: '#f97316' } },
      { value: 45, itemStyle: { color: '#f59e0b' } },
      { value: 90, itemStyle: { color: '#3b82f6' } }
    ],
    barWidth: 30,
    label: { show: true, position: 'top', color: '#e5e7eb', fontSize: 10, formatter: '{c} min' }
  }]
}
</script>

<style scoped>
table { font-size: 12px; width: 100%; table-layout: fixed; }
th {
  color: #9ca3af;
  font-weight: 500;
  text-align: left;
  padding: 8px 8px;
  border-bottom: 1px solid rgba(75, 85, 99, .4);
  background: rgba(31, 41, 55, .6);
  white-space: nowrap;
}
td {
  padding: 8px 8px;
  border-bottom: 1px solid rgba(55, 65, 81, .3);
  vertical-align: middle;
  word-break: break-word;
}
td.nowrap, th.nowrap { white-space: nowrap; }
tr:hover td { background: rgba(59, 130, 246, .05); }

.btn {
  padding: 3px 10px;
  border-radius: 4px;
  font-size: 11px;
  transition: all .2s;
  cursor: pointer;
  white-space: nowrap;
}
.btn-blue { background: rgba(59, 130, 246, .15);  color: #93c5fd; border: 1px solid rgba(59, 130, 246, .3); }
.btn-blue:hover { background: rgba(59, 130, 246, .3); }
.btn-grn  { background: rgba(16, 185, 129, .15);  color: #6ee7b7; border: 1px solid rgba(16, 185, 129, .3); }
.btn-grn:hover  { background: rgba(16, 185, 129, .3); }
</style>
