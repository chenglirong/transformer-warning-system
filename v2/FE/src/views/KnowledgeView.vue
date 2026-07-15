<script setup>
/**
 * 判据知识库总表 —— 只读
 * 后端 REFS(元数据) + 前端 stdRefs(条文摘要/原图静态资源)合并展示;非 RAG、不可在线增删
 * 支持 ?id=722-表5 深链（其它页角标点击跳转）
 */
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import http from '@/service/http'
import { STD_REFS } from '@/data/stdRefs'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const apiItems = ref([])
const filterStd = ref('all')
const q = ref('')
const activeId = ref('')

/** 系统引用的标准原件清单（不含整本 PDF；条文原图见右侧详情） */
const STD_CATALOG = [
  {
    code: 'DL/T 722-2014',
    title: '变压器油中溶解气体分析和判断导则',
    role: '注意值、产气速率、判型步骤、三比值/大卫三角、措施建议与报告版式',
  },
  {
    code: 'DL/T 1498.2-2025',
    title: '变电设备在线监测装置技术规范 第2部分：变压器油中溶解气体',
    role: '在线四档阈值（表A.3）、采集周期与预警后二次采样、最小检测周期',
  },
  {
    code: 'DL/T 1685-2017',
    title: '油浸式变压器（电抗器）状态评价导则',
    role: '附录B：过热/放电缺陷对应停电试验项目',
  },
]

/** 从标题拆章节，补后端未收录条目的 section */
function parseSectionFromTitle(title) {
  const rest = String(title || '').replace(/^DL\/T\s+[\d.]+(?:-\d+)?\s*/, '').trim()
  if (!rest) return ''
  const m = rest.match(
    /^(§[\d.]+(?:\s*[a-z]\))?|A\.\d+(?:\.\d+)?|附录[A-Z](?:\s+(?:图|表)[\w.]+(?:\/(?:表)?[\w.]+)*)?|表[A.\d]+)/,
  )
  return m ? m[0].trim() : rest.split(/\s+/).slice(0, 2).join(' ')
}

const rows = computed(() => {
  const byId = {}
  for (const it of apiItems.value) {
    byId[it.id] = {
      id: it.id,
      std: it.std || '',
      section: it.section || '',
      summary: it.summary || '',
      source: 'be',
    }
  }
  // 前端 stdRefs 补条目 / 补正文与原图
  for (const [id, entry] of Object.entries(STD_REFS)) {
    if (!byId[id]) {
      const m = String(entry.title || '').match(/^(DL\/T\s+[\d.]+(?:-\d+)?)/)
      byId[id] = {
        id,
        std: m ? m[1] : '',
        section: parseSectionFromTitle(entry.title),
        summary: entry.body || '',
        source: 'fe',
      }
    } else if (!byId[id].section) {
      byId[id].section = parseSectionFromTitle(entry.title)
    }
    byId[id].feTitle = entry.title || ''
    byId[id].feBody = entry.body || ''
    byId[id].images = entry.images || (entry.image ? [entry.image] : [])
  }
  return Object.values(byId).sort((a, b) => a.id.localeCompare(b.id, 'zh'))
})

const stdOptions = computed(() => {
  const set = new Set()
  for (const r of rows.value) {
    if (r.std) set.add(r.std)
  }
  return ['all', ...[...set].sort()]
})

const filtered = computed(() => {
  let list = rows.value
  if (filterStd.value !== 'all') {
    list = list.filter((r) => r.std === filterStd.value)
  }
  const key = q.value.trim().toLowerCase()
  if (key) {
    list = list.filter((r) => {
      const blob = `${r.id} ${r.std} ${r.section} ${r.summary} ${r.feTitle} ${r.feBody}`.toLowerCase()
      return blob.includes(key)
    })
  }
  return list
})

const active = computed(() => {
  const hit = rows.value.find((r) => r.id === activeId.value)
  if (hit) return hit
  return filtered.value[0] || null
})

/** 各标准下已挂接的章节条目（点章节可跳详情） */
const catalogCards = computed(() => {
  return STD_CATALOG.map((s) => {
    const items = rows.value
      .filter((r) => r.std === s.code)
      .map((r) => ({
        id: r.id,
        section: r.section || r.feTitle || r.id,
        hasImg: (r.images || []).length > 0,
      }))
    return { ...s, items, count: items.length }
  })
})

function queryId() {
  return typeof route.query.id === 'string' ? route.query.id : ''
}

/** 按深链选中；若被筛选隐藏则清筛选 */
function focusId(id, { syncRoute = false } = {}) {
  if (!id) return false
  const hit = rows.value.find((r) => r.id === id)
  if (!hit) return false
  if (filterStd.value !== 'all' && hit.std !== filterStd.value) {
    filterStd.value = 'all'
  }
  if (q.value.trim()) q.value = ''
  activeId.value = id
  if (syncRoute && route.query.id !== id) {
    router.replace({ path: '/knowledge', query: { id } })
  }
  return true
}

function selectRow(id) {
  focusId(id, { syncRoute: true })
}

function filterByStd(code) {
  filterStd.value = code
  q.value = ''
  nextTick(() => {
    const stillVisible = filtered.value.some((r) => r.id === activeId.value)
    if (!stillVisible && filtered.value.length) {
      activeId.value = filtered.value[0].id
      router.replace({ path: '/knowledge', query: { id: filtered.value[0].id } })
    }
  })
}

function onChipFilter(code) {
  filterStd.value = code
  q.value = ''
  nextTick(() => {
    const stillVisible = filtered.value.some((r) => r.id === activeId.value)
    if (!stillVisible && filtered.value.length) {
      activeId.value = filtered.value[0].id
      router.replace({ path: '/knowledge', query: { id: filtered.value[0].id } })
    }
  })
}

function applyRouteId() {
  const id = queryId()
  if (id && focusId(id)) return
  if (!activeId.value && filtered.value.length) {
    activeId.value = filtered.value[0].id
  }
}

onMounted(async () => {
  try {
    const res = await http.get('/agent/knowledge')
    apiItems.value = res.items || []
  } catch {
    apiItems.value = []
  } finally {
    loading.value = false
    await nextTick()
    applyRouteId()
  }
})

watch(() => route.query.id, () => {
  if (!loading.value) applyRouteId()
})
</script>

<template>
  <div v-loading="loading" class="kb">
    <section class="gp catalog">
      <div class="gp-head">
        <span class="gp-title">引用标准清单</span>
        <span class="gp-sub">{{ rows.length }} 条判据 · {{ STD_CATALOG.length }} 项标准</span>
      </div>
      <div class="gp-body catalog-grid">
        <article
          v-for="c in catalogCards"
          :key="c.code"
          class="cat-card"
          :class="{ on: filterStd === c.code }"
          @click="filterByStd(c.code)"
        >
          <div class="cat-head">
            <div class="cat-code mono">{{ c.code }}</div>
            <div class="cat-title">{{ c.title }}</div>
            <div class="cat-role">{{ c.role }}</div>
            <div class="cat-meta">{{ c.count }} 条</div>
          </div>
          <div class="cat-secs">
            <button
              v-for="it in c.items"
              :key="it.id"
              type="button"
              class="cat-sec"
              :class="{ on: active && active.id === it.id }"
              :title="it.id"
              @click.stop="selectRow(it.id)"
            >
              <span class="cat-sec-label">{{ it.section }}</span>
              <span v-if="it.hasImg" class="cat-sec-img">图</span>
            </button>
          </div>
        </article>
      </div>
    </section>

    <section class="gp">
      <div class="gp-head toolbar">
        <div class="chips">
          <button
            v-for="s in stdOptions"
            :key="s"
            type="button"
            class="chip"
            :class="{ on: filterStd === s }"
            @click="onChipFilter(s)"
          >
            {{ s === 'all' ? '全部标准' : s }}
          </button>
        </div>
        <input
          v-model="q"
          type="search"
          class="search"
          placeholder="搜索 id / 章节 / 摘要…"
        />
        <span class="head-ref">共 {{ filtered.length }} 条</span>
      </div>

      <div class="gp-body kb-layout">
        <div class="table-wrap">
          <table class="kb-table">
            <thead>
              <tr>
                <th style="width:9em">id</th>
                <th style="width:11em">标准</th>
                <th style="width:8em">章节</th>
                <th>摘要</th>
                <th style="width:3em" class="nowrap">原图</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="r in filtered"
                :key="r.id"
                :class="{ on: active && active.id === r.id }"
                @click="selectRow(r.id)"
              >
                <td class="mono cite-id">{{ r.id }}</td>
                <td>{{ r.std || '—' }}</td>
                <td class="mono">{{ r.section || '—' }}</td>
                <td class="sum">{{ r.summary || r.feBody || '—' }}</td>
                <td class="nowrap">{{ (r.images || []).length ? '有' : '—' }}</td>
              </tr>
              <tr v-if="!filtered.length">
                <td colspan="5" class="empty">无匹配条目</td>
              </tr>
            </tbody>
          </table>
        </div>

        <aside v-if="active" class="detail">
          <div class="detail-head">
            <span class="mono cite-id">{{ active.id }}</span>
            <span class="detail-std">{{ active.std }}</span>
          </div>
          <div class="detail-sec mono">{{ active.section || '—' }}</div>
          <h3 class="detail-title">{{ active.feTitle || active.summary }}</h3>
          <p class="detail-body">{{ active.feBody || active.summary }}</p>
          <div v-if="(active.images || []).length" class="detail-imgs">
            <img
              v-for="(src, i) in active.images"
              :key="i"
              :src="src"
              :alt="active.id"
            />
          </div>
        </aside>
      </div>
    </section>
  </div>
</template>

<style scoped>
.kb { display: flex; flex-direction: column; gap: 12px; }

.catalog .gp-head {
  display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px 14px;
}
.gp-title { font-size: 13px; font-weight: 650; color: var(--fg); }
.gp-sub { font-size: 11px; color: var(--fg-4); }
.catalog-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  padding-top: 4px !important;
}
@media (max-width: 1100px) {
  .catalog-grid { grid-template-columns: 1fr; }
}
.cat-card {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--bg-3);
  overflow: hidden;
  cursor: pointer;
}
.cat-card:hover {
  border-color: rgba(45, 212, 191, 0.3);
}
.cat-card.on {
  border-color: rgba(45, 212, 191, 0.45);
  box-shadow: inset 0 0 0 1px rgba(45, 212, 191, 0.15);
}
.cat-head {
  display: block;
  padding: 12px 12px 8px;
  color: inherit;
}
.cat-card:hover .cat-code { color: #5eead4; }
.cat-code {
  font-size: 12px; font-weight: 700; color: var(--teal-2);
  margin-bottom: 4px;
}
.cat-title {
  font-size: 12.5px; font-weight: 650; color: var(--fg);
  line-height: 1.4; margin-bottom: 6px;
}
.cat-role {
  font-size: 11.5px; color: var(--fg-3); line-height: 1.5;
  margin-bottom: 6px;
}
.cat-meta { font-size: 10.5px; color: var(--fg-4); }
.cat-secs {
  display: flex; flex-wrap: wrap; gap: 5px;
  padding: 0 12px 12px;
}
.cat-sec {
  display: inline-flex; align-items: center; gap: 4px;
  border: 1px solid var(--line);
  background: var(--bg-2);
  color: var(--fg-3);
  font-size: 10.5px; padding: 3px 8px; border-radius: 999px;
  cursor: pointer; max-width: 100%;
}
.cat-sec:hover, .cat-sec.on {
  border-color: rgba(45, 212, 191, 0.45);
  color: #5eead4;
  background: rgba(45, 212, 191, 0.1);
}
.cat-sec-label {
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  max-width: 14em;
  font-family: 'JetBrains Mono', monospace;
}
.cat-sec-img {
  flex-shrink: 0;
  font-size: 9px; font-weight: 700;
  color: #5eead4; opacity: 0.85;
}

.toolbar {
  display: flex; flex-wrap: wrap; align-items: center; gap: 10px 14px;
}
.chips { display: flex; flex-wrap: wrap; gap: 6px; flex: 1; }
.chip {
  border: 1px solid var(--line);
  background: var(--bg-3);
  color: var(--fg-3);
  font-size: 11px; padding: 4px 10px; border-radius: 999px;
  cursor: pointer;
}
.chip.on {
  border-color: rgba(45, 212, 191, 0.45);
  color: #5eead4;
  background: rgba(45, 212, 191, 0.1);
}
.search {
  width: min(240px, 100%);
  height: 30px;
  padding: 0 10px;
  border-radius: 6px;
  border: 1px solid var(--line-2);
  background: var(--bg-3);
  color: var(--fg);
  font-size: 12px;
}
.head-ref {
  margin-left: auto;
  font-size: 11px;
  color: var(--fg-4);
  font-weight: 600;
  white-space: nowrap;
}

.kb-layout {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 12px;
  padding-top: 4px !important;
}
@media (max-width: 1100px) {
  .kb-layout { grid-template-columns: 1fr; }
}

.table-wrap {
  overflow: auto;
  max-height: calc(100vh - 280px);
  border: 1px solid var(--line);
  border-radius: 8px;
}
.kb-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.kb-table thead th {
  position: sticky; top: 0; z-index: 1;
  background: var(--bg-3);
  text-align: left;
  padding: 8px 10px;
  color: var(--fg-3);
  font-weight: 650;
  border-bottom: 1px solid var(--line);
}
.kb-table td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--line);
  vertical-align: top;
  color: var(--fg-2);
}
.kb-table tbody tr { cursor: pointer; }
.kb-table tbody tr:hover td { background: rgba(45, 212, 191, 0.05); }
.kb-table tbody tr.on td { background: rgba(45, 212, 191, 0.1); }
.mono { font-family: 'JetBrains Mono', monospace; font-size: 11px; }
.cite-id { color: var(--teal-2); font-weight: 650; }
.nowrap { white-space: nowrap; }
.sum { line-height: 1.45; color: var(--fg-3); }
.empty { text-align: center; color: var(--fg-4); padding: 24px !important; }

.detail {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--bg-3);
  padding: 14px;
  max-height: calc(100vh - 280px);
  overflow-y: auto;
}
.detail-head {
  display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
}
.detail-std { font-size: 11px; color: var(--teal-2); font-weight: 650; }
.detail-sec { margin-top: 6px; font-size: 11px; color: var(--fg-4); }
.detail-title {
  margin: 12px 0 8px;
  font-size: 14px; color: var(--fg);
  font-weight: 650; line-height: 1.4;
}
.detail-body {
  margin: 0;
  font-size: 12.5px; color: var(--fg-2); line-height: 1.65;
}
.detail-imgs { margin-top: 12px; display: flex; flex-direction: column; gap: 10px; }
.detail-imgs img {
  width: 100%;
  border-radius: 6px;
  border: 1px solid var(--line);
  background: #1c2530;
}
</style>
