<script setup>
/** 列表表格统一分页底栏 */
import { computed, watch } from 'vue'

const props = defineProps({
  total: { type: Number, default: 0 },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: 20 },
  pageSizeOptions: { type: Array, default: () => [20, 50, 100] },
  emptyText: { type: String, default: '无匹配记录' },
  showPageSize: { type: Boolean, default: true },
})

const emit = defineEmits(['update:page', 'update:pageSize'])

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

const totalText = computed(() => {
  const n = props.total
  if (!n) return props.emptyText
  return `共 ${n} 条`
})

const pageNums = computed(() => {
  const max = totalPages.value
  const cur = props.page
  if (max <= 7) return Array.from({ length: max }, (_, i) => i + 1)
  const pages = [1]
  const start = Math.max(2, cur - 1)
  const end = Math.min(max - 1, cur + 1)
  if (start > 2) pages.push('…')
  for (let p = start; p <= end; p++) pages.push(p)
  if (end < max - 1) pages.push('…')
  pages.push(max)
  return pages
})

watch(totalPages, (max) => {
  if (props.page > max) emit('update:page', max)
})

function setPage(n) {
  emit('update:page', n)
}

function onPageSizeChange(e) {
  const v = Number(e.target.value)
  emit('update:pageSize', v)
  emit('update:page', 1)
}
</script>

<template>
  <div class="foot">
    <div class="foot-meta">
      <label v-if="showPageSize && pageSizeOptions.length" class="page-size">
        每页
        <select :value="pageSize" @change="onPageSizeChange">
          <option v-for="opt in pageSizeOptions" :key="opt" :value="opt">{{ opt }}</option>
        </select>
        条
      </label>
      <span class="muted">{{ totalText }}</span>
    </div>
    <div class="pager">
      <button type="button" class="page-btn" :disabled="page <= 1" @click="setPage(page - 1)">上一页</button>
      <template v-for="(n, i) in pageNums" :key="i">
        <span v-if="n === '…'" class="ellipsis">…</span>
        <button
          v-else
          type="button"
          class="page-btn"
          :class="{ on: n === page }"
          @click="setPage(n)"
        >
          {{ n }}
        </button>
      </template>
      <button type="button" class="page-btn" :disabled="page >= totalPages" @click="setPage(page + 1)">下一页</button>
    </div>
  </div>
</template>
