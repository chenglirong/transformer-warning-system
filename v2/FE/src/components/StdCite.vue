<script setup>
// 国标角标:悬停展示条文摘要 + 原图(若有)
import { computed } from 'vue'
import { resolveStd } from '@/data/stdRefs'

const props = defineProps({
  /** 条目 id(如 722-表5)或展示文案(如 §10.1 表5) */
  refId: { type: String, required: true },
  /** 角标上显示的文字;默认用 refId */
  label: { type: String, default: '' },
  /** 文内角标(不顶到右侧) */
  inline: { type: Boolean, default: false },
})

const entry = computed(() => resolveStd(props.refId))
const text = computed(() => props.label || props.refId)
</script>

<template>
  <span class="std-cite-wrap" :class="{ inline }">
    <el-popover
      v-if="entry"
      placement="bottom-end"
      :width="420"
      trigger="hover"
      :show-after="120"
      :hide-after="80"
      popper-class="std-cite-pop"
    >
      <template #reference>
        <span class="std-cite" tabindex="0">{{ text }}</span>
      </template>
      <div class="cite-head">{{ entry.title }}</div>
      <div class="cite-body">{{ entry.body }}</div>
      <img
        v-for="(src, i) in (entry.images || (entry.image ? [entry.image] : []))"
        :key="i"
        :src="src"
        class="cite-img"
        :alt="entry.title"
      />
    </el-popover>
    <span v-else class="std-cite bare">{{ text }}</span>
  </span>
</template>

<style scoped>
.std-cite-wrap { margin-left: auto; display: inline-flex; align-items: center; }
.std-cite-wrap.inline { margin-left: 0; vertical-align: baseline; }
.std-cite {
  font-size: 9.5px;
  font-weight: 600;
  color: var(--teal-2);
  font-family: 'JetBrains Mono', monospace;
  cursor: help;
  border-bottom: 1px dotted var(--teal-line);
  opacity: 0.95;
  white-space: nowrap;
}
.std-cite-wrap.inline .std-cite {
  font-size: 11px;
  margin: 0 1px;
}
.std-cite.bare { border-bottom: none; cursor: default; opacity: 0.7; }
</style>

<style>
.std-cite-pop.el-popper {
  background: #323e4c !important;
  border: 1px solid rgba(45, 212, 191, 0.35) !important;
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.45) !important;
  padding: 12px 14px !important;
  max-width: 520px;
  max-height: 80vh;
  overflow-y: auto;
}
.std-cite-pop .el-popper__arrow::before {
  background: #323e4c !important;
  border: 1px solid rgba(45, 212, 191, 0.35) !important;
}
.std-cite-pop .cite-head {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  color: #5eead4;
  margin-bottom: 6px;
  line-height: 1.4;
}
.std-cite-pop .cite-body {
  font-size: 12px;
  color: #b4c0d4;
  line-height: 1.65;
}
.std-cite-pop .cite-img {
  display: block;
  width: 100%;
  margin-top: 10px;
  border-radius: 4px;
  border: 1px solid rgba(160, 174, 192, 0.2);
  background: #1c2530;
}
</style>
