<script setup>
/** 国标角标：点击跳转判据知识库对应条目（原图集中在 /knowledge 展示） */
import { computed } from 'vue'
import { resolveStd } from '@/data/stdRefs'

const props = defineProps({
  /** 条目 id(如 722-表5)或旧文案(如 §10.1 表5)，均解析到标准 id */
  refId: { type: String, required: true },
  /** 兼容旧调用；展示一律用解析后的 id，忽略 label */
  label: { type: String, default: '' },
  /** 文内角标(不顶到右侧) */
  inline: { type: Boolean, default: false },
})

const entry = computed(() => resolveStd(props.refId))
const citeId = computed(() => entry.value?.id || props.refId)
const text = computed(() => citeId.value)
</script>

<template>
  <router-link
    v-if="entry"
    class="std-cite-wrap"
    :class="{ inline }"
    :to="{ path: '/knowledge', query: { id: citeId } }"
    :title="`${entry.title} · 查看原图`"
  >
    <span class="std-cite">{{ text }}</span>
  </router-link>
  <span v-else class="std-cite-wrap" :class="{ inline }">
    <span class="std-cite bare">{{ text }}</span>
  </span>
</template>

<style scoped>
.std-cite-wrap {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  text-decoration: none;
  color: inherit;
}
.std-cite-wrap.inline { margin-left: 0; vertical-align: baseline; }
.std-cite {
  font-size: 9.5px;
  font-weight: 600;
  color: var(--teal-2);
  font-family: 'JetBrains Mono', monospace;
  cursor: pointer;
  border-bottom: 1px dotted var(--teal-line);
  opacity: 0.95;
  white-space: nowrap;
}
.std-cite-wrap.inline .std-cite {
  font-size: 11px;
  margin: 0 1px;
}
.std-cite.bare { border-bottom: none; cursor: default; opacity: 0.7; }
.std-cite-wrap:hover .std-cite {
  color: #5eead4;
  border-bottom-style: solid;
}
</style>
