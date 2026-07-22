<script setup>
// 数据集 —— 360 天 7 气原始记录，选日定位 + 下钻分级检测
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import http from '@/service/http'
import TablePager from '@/components/TablePager.vue'

const router = useRouter()
const route = useRoute()
const loading = ref(true)
const allRecords = ref([])
const selectedDate = ref('')

const page = ref(1)
const pageSize = ref(20)

const GAS_COLS = [
  { key: 'h2', label: 'H₂', unit: 'μL/L' },
  { key: 'ch4', label: 'CH₄', unit: 'μL/L' },
  { key: 'c2h4', label: 'C₂H₄', unit: 'μL/L' },
  { key: 'c2h6', label: 'C₂H₆', unit: 'μL/L' },
  { key: 'c2h2', label: 'C₂H₂', unit: 'μL/L' },
  { key: 'co', label: 'CO', unit: 'μL/L' },
  { key: 'co2', label: 'CO₂', unit: 'μL/L' },
]

const dateSet = computed(() => new Set(allRecords.value.map((r) => r.date)))
const dateRange = computed(() => {
  if (!allRecords.value.length) return null
  const last = allRecords.value.length - 1
  return [allRecords.value[last].date, allRecords.value[0].date]
})
const idx = computed(() => allRecords.value.findIndex((r) => r.date === selectedDate.value))

const pageRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return allRecords.value.slice(start, start + pageSize.value)
})

function formatDate(d) {
  if (!d) return ''
  if (typeof d === 'string') return d.slice(0, 10)
  const dt = d instanceof Date ? d : new Date(d)
  if (Number.isNaN(dt.getTime())) return ''
  const y = dt.getFullYear()
  const m = String(dt.getMonth() + 1).padStart(2, '0')
  const day = String(dt.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function disabledDate(d) {
  if (!dateRange.value) return true
  const iso = formatDate(d)
  return !dateSet.value.has(iso)
}

function stepDay(delta) {
  const i = idx.value - delta
  if (i < 0 || i >= allRecords.value.length) return
  selectedDate.value = allRecords.value[i].date
}

function goDetect(date) {
  router.push({ path: '/detect', query: { date } })
}

function jumpToSelectedDate(d) {
  if (!d) return
  const i = allRecords.value.findIndex((r) => r.date === d)
  if (i >= 0) page.value = Math.floor(i / pageSize.value) + 1
}

watch(pageSize, () => { page.value = 1 })
watch(selectedDate, (d) => jumpToSelectedDate(d))
watch(
  () => route.query.date,
  (q) => {
    if (typeof q === 'string' && q && allRecords.value.some((r) => r.date === q)) {
      selectedDate.value = q
    }
  },
)

onMounted(async () => {
  loading.value = true
  try {
    const res = await http.get('/dataset/records')
    allRecords.value = res?.records || []
    const q = typeof route.query.date === 'string' ? route.query.date : ''
    selectedDate.value =
      q && allRecords.value.some((r) => r.date === q)
        ? q
        : allRecords.value[0]?.date || ''
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div v-if="loading" class="state">加载中…</div>
  <div v-else class="dataset-page page-list">
    <section class="gp list-panel">
      <div class="toolbar">
        <div class="nav">
          <button
            type="button"
            class="btn btn-ghost"
            :disabled="idx < 0 || idx >= allRecords.length - 1"
            @click="stepDay(-1)"
          >
            ‹ 前日
          </button>
          <el-date-picker
            v-model="selectedDate"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            :disabled-date="disabledDate"
            popper-class="dga-cal-popper"
            class="date-pick"
          />
          <button
            type="button"
            class="btn btn-ghost"
            :disabled="idx <= 0"
            @click="stepDay(1)"
          >
            后日 ›
          </button>
        </div>
      </div>

      <div class="table-wrap table-wrap--bordered">
        <table class="dga-table">
          <thead>
            <tr>
              <th class="col-date">日期</th>
              <th v-for="g in GAS_COLS" :key="g.key" class="num col-gas">{{ g.label }} ({{ g.unit }})</th>
              <th class="col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="r in pageRows"
              :key="r.date"
              :class="{ on: r.date === selectedDate }"
            >
              <td class="mono col-date">{{ r.date }}</td>
              <td v-for="g in GAS_COLS" :key="g.key" class="num mono">{{ r[g.key] ?? '—' }}</td>
              <td class="col-actions">
                <button type="button" class="act-btn teal" @click="goDetect(r.date)">分级检测</button>
              </td>
            </tr>
            <tr v-if="!pageRows.length">
              <td :colspan="GAS_COLS.length + 2" class="empty">无记录</td>
            </tr>
          </tbody>
        </table>
      </div>

      <TablePager
        v-model:page="page"
        v-model:page-size="pageSize"
        :total="allRecords.length"
        :page-size-options="[20, 50, 100]"
      />
    </section>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  padding: 12px 14px 10px;
  flex-shrink: 0;
}
.nav {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.date-pick { width: 160px; }

.col-date { width: 108px; }

.state { padding: 48px; text-align: center; color: var(--fg-4); }
</style>
